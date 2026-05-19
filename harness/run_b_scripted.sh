#!/usr/bin/env bash
# Scripted Spec Kit replication for Workflow B.
#
# Drives one benchmark cell end-to-end:
#   1. branches workflow-b/task-N/run-M off spec-kit-base (which has
#      `specify init --here --integration claude` already committed),
#      copies the project guardrails CLAUDE.md into target/, resets
#      target/app.db
#   2. extracts the task prompt body from tasks/0N-*.md
#   3. drives a single Claude Code session through the five Spec Kit
#      phases by chaining --resume:
#         constitution → specify → plan → tasks → implement
#      Each phase invokes the corresponding /speckit-* skill via
#      natural-language instruction so the agent loads the skill from
#      target/.claude/skills/. The constitution body is the verbatim
#      block from workflows/b-spec-kit.md.
#   4. captures JSON output of each phase under
#      results/runs/b-N-M/phase-{1..5}-*.json, sums cost / tokens
#   5. saves spec.md / plan.md / tasks.md verbatim from
#      target/specs/<feature>/ if Spec Kit wrote them there
#   6. invokes harness/run.py --non-interactive --skip-branch with the
#      aggregate values
#
# Same hermetic pattern as run_a_scripted.sh: one fresh empty HOME
# reused across all five phases (so --resume can find session state),
# OAuth token from --token-file. Model: sonnet.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TASK=""
RUN=""
SCORE=""
NOTES=""
RECORD=1
MODEL="sonnet"
TOKEN_FILE="${CLAUDE_BENCH_TOKEN_FILE:-$HOME/.config/claude-bench/oauth-token}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task) TASK="$2"; shift 2 ;;
        --run) RUN="$2"; shift 2 ;;
        --score) SCORE="$2"; shift 2 ;;
        --notes) NOTES="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --token-file) TOKEN_FILE="$2"; shift 2 ;;
        --no-record) RECORD=0; shift ;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

[[ -z "$TASK" || -z "$RUN" ]] && { echo "missing --task / --run" >&2; exit 2; }
[[ "$TASK" =~ ^[1-4]$ ]] || { echo "--task must be 1..4" >&2; exit 2; }
[[ "$RUN" =~ ^[1-3]$ ]] || { echo "--run must be 1..3" >&2; exit 2; }
if [[ "$RECORD" == 1 && ( -z "$SCORE" || -z "$NOTES" ) ]]; then
    echo "--score and --notes required unless --no-record" >&2
    exit 2
fi

VENV_PY="$REPO_ROOT/target/.venv/bin/python"
[[ -x "$VENV_PY" ]] || { echo "venv python missing at $VENV_PY" >&2; exit 2; }

[[ -f "$TOKEN_FILE" ]] || {
    echo "OAuth token file not found at $TOKEN_FILE" >&2
    exit 2
}
CLAUDE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")"
[[ -n "$CLAUDE_OAUTH_TOKEN" ]] || { echo "token file is empty" >&2; exit 2; }

TASK_FILE_NAMES=( [1]=01-trivial.md [2]=02-medium.md [3]=03-ambiguous.md [4]=04-brownfield.md )
TASK_FILE="$REPO_ROOT/tasks/${TASK_FILE_NAMES[$TASK]}"
[[ -f "$TASK_FILE" ]] || { echo "task file missing: $TASK_FILE" >&2; exit 2; }

BRANCH="workflow-b/task-${TASK}/run-${RUN}"
BASE="spec-kit-base"
ART_DIR="$REPO_ROOT/results/runs/b-${TASK}-${RUN}"
mkdir -p "$ART_DIR"

# --- 1. branch + reset ----------------------------------------------------
if [[ -n "$(git status --porcelain)" ]]; then
    echo "working tree dirty; refusing to start" >&2
    git status --short >&2
    exit 2
fi
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    echo "branch $BRANCH already exists; delete it first" >&2
    exit 2
fi
git checkout "$BASE" >/dev/null
git checkout -b "$BRANCH" >/dev/null
echo "checked out $BRANCH off $BASE"

cp "$REPO_ROOT/workflows/claude-md-template/CLAUDE.md" "$REPO_ROOT/target/CLAUDE.md"
rm -f "$REPO_ROOT/target/app.db"

# --- 2. extract prompt + constitution -------------------------------------
PROMPT="$(awk '
    /^## Prompt/ { capture=1; next }
    capture && /^## / { exit }
    capture { print }
' "$TASK_FILE" | sed -e '/./,$!d' -e :a -e '/^\n*$/{$d;N;ba' -e '}')"
[[ -z "$PROMPT" ]] && { echo "could not extract prompt" >&2; exit 2; }
PROMPT_HASH="sha256:$(printf '%s' "$PROMPT" | shasum -a 256 | awk '{print $1}')"

# Verbatim constitution body from workflows/b-spec-kit.md
IFS='' read -r -d '' CONSTITUTION_BODY <<'EOF' || true
# Project constitution

- Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.
- Idiomatic FastAPI: small route functions, Pydantic models for
  request and response shapes, dependency injection via Depends.
- Tests are non-optional. Minimum 80% line coverage on changed files.
  Every new route ships with happy-path and at least one error-path
  test.
- Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.
- No new third-party dependencies without a stated justification.
- Type hints on every public function and route handler.
- Don't refactor unrelated code in the same change.
EOF

# --- 3. drive the five phases ---------------------------------------------
CLEAN_HOME="$(mktemp -d -t claude-bench-home-XXXXXX)"
trap 'rm -rf "$CLEAN_HOME"' EXIT

# call_claude <phase-name> <phase-num> [resume-session-or-empty] <prompt-text>
# Writes JSON to $ART_DIR/phase-<N>-<name>.json and prints the session_id.
call_claude() {
    local name="$1"; local n="$2"; local resume="$3"; local text="$4"
    local out="$ART_DIR/phase-${n}-${name}.json"
    local resume_arg=""
    if [[ -n "$resume" ]]; then
        resume_arg="--resume $resume"
    fi
    (
        cd "$REPO_ROOT/target"
        HOME="$CLEAN_HOME" CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_OAUTH_TOKEN" \
        claude --print \
            --model "$MODEL" \
            --add-dir "$REPO_ROOT/target" \
            $resume_arg \
            --permission-mode bypassPermissions \
            --output-format json \
            "$text" > "$out"
    )
    jq -r .session_id "$out"
}

START_TS=$(date +%s)

echo "→ phase 1: /speckit-constitution"
PHASE1_PROMPT="Use the speckit-constitution skill to set up the project constitution. Use the following content verbatim as the constitution body, do not modify or expand it:

$CONSTITUTION_BODY"
SID="$(call_claude constitution 1 "" "$PHASE1_PROMPT")"
echo "  session: $SID"

echo "→ phase 2: /speckit-specify"
PHASE2_PROMPT="Use the speckit-specify skill to create a feature specification. The user request is exactly this — do not expand or reinterpret beyond what Spec Kit would do natively:

$PROMPT"
call_claude specify 2 "$SID" "$PHASE2_PROMPT" >/dev/null

echo "→ phase 3: /speckit-plan"
call_claude plan 3 "$SID" "Use the speckit-plan skill. Accept defaults; produce the implementation plan for the spec we just wrote." >/dev/null

echo "→ phase 4: /speckit-tasks"
call_claude tasks 4 "$SID" "Use the speckit-tasks skill. Accept defaults; decompose the plan into actionable tasks." >/dev/null

echo "→ phase 5: /speckit-implement"
call_claude implement 5 "$SID" "Use the speckit-implement skill. Run the implementation tasks end-to-end. Run pytest at the end; the run is only complete when tests pass." >/dev/null

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

# --- 4. aggregate cost / tokens -------------------------------------------
TOTAL_COST=$(jq -s '[.[].total_cost_usd] | add' "$ART_DIR"/phase-*.json)
TOTAL_IN=$(jq -s '[.[].usage.input_tokens] | add' "$ART_DIR"/phase-*.json)
TOTAL_OUT=$(jq -s '[.[].usage.output_tokens] | add' "$ART_DIR"/phase-*.json)

# per-phase breakdown for run-meta.json
PHASE_COSTS=$(jq -n \
    --slurpfile c "$ART_DIR/phase-1-constitution.json" \
    --slurpfile s "$ART_DIR/phase-2-specify.json" \
    --slurpfile p "$ART_DIR/phase-3-plan.json" \
    --slurpfile t "$ART_DIR/phase-4-tasks.json" \
    --slurpfile i "$ART_DIR/phase-5-implement.json" \
    '{
      constitution: $c[0].total_cost_usd,
      specify: $s[0].total_cost_usd,
      plan: $p[0].total_cost_usd,
      tasks: $t[0].total_cost_usd,
      implement: $i[0].total_cost_usd
    }')

# --- 5. copy spec/plan/tasks artifacts ------------------------------------
# Spec Kit writes to target/specs/<feature-slug>/ — find the newest one
# created during this run and snapshot the markdown into the artifact dir.
if compgen -G "$REPO_ROOT/target/specs/*/" >/dev/null; then
    FEATURE_DIR="$(ls -dt "$REPO_ROOT"/target/specs/*/ | head -1)"
    for f in spec.md plan.md tasks.md research.md data-model.md quickstart.md; do
        if [[ -f "$FEATURE_DIR/$f" ]]; then
            cp "$FEATURE_DIR/$f" "$ART_DIR/$f"
        fi
    done
fi

# --- 6. meta artifact -----------------------------------------------------
cat > "$ART_DIR/run-meta.json" <<EOF
{
  "workflow": "b",
  "task": $TASK,
  "run": $RUN,
  "label": "Scripted Spec Kit replication",
  "branch": "$BRANCH",
  "base_branch": "$BASE",
  "prompt_hash": "$PROMPT_HASH",
  "session_id": "$SID",
  "model": "$MODEL",
  "hermetic_mode": true,
  "context_source": "target_only",
  "duration_seconds": $DURATION,
  "phase_costs_usd": $PHASE_COSTS,
  "total_cost_usd": $TOTAL_COST,
  "total_tokens_input": $TOTAL_IN,
  "total_tokens_output": $TOTAL_OUT
}
EOF

echo
echo "captured: $(ls "$ART_DIR" | tr '\n' ' ')"
echo "duration: ${DURATION}s   total cost: \$${TOTAL_COST}"

# --- commit workflow's edits on the run branch ----------------------------
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain target/)" ]]; then
    git -C "$REPO_ROOT" add target/
    git -C "$REPO_ROOT" \
        -c user.name="claude-bench" \
        -c user.email="claude-bench@local" \
        commit -m "$BRANCH: workflow output

Captured by harness/run_b_scripted.sh (Spec Kit 5-phase). See
results/runs/b-${TASK}-${RUN}/ on main for phase JSON transcripts,
spec.md / plan.md / tasks.md (if Spec Kit wrote them), and
run-meta.json." \
        >/dev/null
    echo "→ committed workflow edits on $BRANCH"
fi

# --- 7. record row --------------------------------------------------------
if [[ "$RECORD" == 0 ]]; then
    echo "--no-record set; skipping harness/run.py invocation."
    exit 0
fi

"$VENV_PY" "$REPO_ROOT/harness/run.py" \
    --workflow b --task "$TASK" --run "$RUN" \
    --non-interactive --skip-branch \
    --duration-seconds "$DURATION" \
    --prompt-hash "$PROMPT_HASH" \
    --total-cost-usd "$TOTAL_COST" \
    --total-tokens-input "$TOTAL_IN" \
    --total-tokens-output "$TOTAL_OUT" \
    --model "$MODEL" \
    --hermetic-mode true \
    --context-source target_only \
    --score "$SCORE" \
    --notes "$NOTES"
