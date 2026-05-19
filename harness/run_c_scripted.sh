#!/usr/bin/env bash
# Scripted BMAD persona-chain replication for Workflow C.
#
# Drives one benchmark cell through BMAD's v6.7.1 persona chain. The
# chain length depends on the task per workflows/c-bmad.md:
#
#   Task 1: dev → code-review                                       (2)
#   Task 2: pm → architect → create-story → dev → code-review       (5)
#   Task 3: analyst → pm → architect → check-readiness →
#           create-story → dev → code-review                        (7)
#   Task 4: pm → architect → party-mode → create-story →
#           dev → code-review                                       (6)
#
# Each persona is a Claude Code skill installed at
# target/.claude/skills/<bmad-*>/, inherited from the bmad-base branch.
# Persona handoff prompts come verbatim from workflows/c-bmad.md.
#
# All personas run in a single Claude Code session chained with
# --resume so context flows persona-to-persona (the runbook is
# explicit: don't compress handoffs, that defeats the experiment).
# Same hermetic pattern as the other scripted runners.

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

BRANCH="workflow-c/task-${TASK}/run-${RUN}"
BASE="bmad-base"
ART_DIR="$REPO_ROOT/results/runs/c-${TASK}-${RUN}"
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

# --- 2. extract prompt ----------------------------------------------------
PROMPT="$(awk '
    /^## Prompt/ { capture=1; next }
    capture && /^## / { exit }
    capture { print }
' "$TASK_FILE" | sed -e '/./,$!d' -e :a -e '/^\n*$/{$d;N;ba' -e '}')"
[[ -z "$PROMPT" ]] && { echo "could not extract prompt" >&2; exit 2; }
PROMPT_HASH="sha256:$(printf '%s' "$PROMPT" | shasum -a 256 | awk '{print $1}')"

# --- 3. persona chain per task -------------------------------------------
# Format: "<persona-skill>:<prompt-template-key>"
# Prompt templates below substitute {PROMPT} or {ARCHDESIGN}.
case "$TASK" in
    1) CHAIN=(dev code-review) ;;
    2) CHAIN=(pm architect create-story dev code-review) ;;
    3) CHAIN=(analyst pm architect check-readiness create-story dev code-review) ;;
    4) CHAIN=(pm architect party-mode create-story dev code-review) ;;
esac

prompt_for() {
    case "$1" in
        analyst)
            cat <<EOT
Use the bmad-agent-analyst skill.

We have a new request: $PROMPT

Elicit any missing requirements you need. Produce a brief that the PM can use. When you have what you need, hand off to bmad-agent-pm by stating "ready for PM handoff" and summarising the brief.
EOT
            ;;
        pm)
            cat <<EOT
Use the bmad-agent-pm skill.

Take the Analyst's brief if one exists in this session, otherwise treat the raw request below as the input:

$PROMPT

Produce a PRD: goals, non-goals, acceptance criteria, open questions. When done, state "ready for architect handoff".
EOT
            ;;
        architect)
            cat <<EOT
Use the bmad-agent-architect skill.

Take the PRD from this session. Produce a technical design that fits the existing codebase. Read the relevant code first (start from src/api/). Identify which files change and how. When done, state "ready for next handoff".
EOT
            ;;
        party-mode)
            cat <<EOT
Use the bmad-party-mode skill.

Convention sweep. We have a small brownfield service and we are about to implement the architect's design from this session. Multiple personas: read the codebase and surface every implicit convention or gotcha the Dev needs to respect, especially around shared types, units, and storage formats. Produce a short numbered list.
EOT
            ;;
        check-readiness)
            cat <<EOT
Use the bmad-check-implementation-readiness skill (acting as Product Owner).

Take the architect's design from this session. Verify each piece of work has clear acceptance criteria and is ready to be sliced into stories. Flag any gaps. When green, state "ready for story creation".
EOT
            ;;
        create-story)
            cat <<EOT
Use the bmad-create-story skill (acting as Scrum Master).

Sequence the work into stories. For each, write a one-paragraph "ready for dev" brief with acceptance criteria. Then hand off to bmad-agent-dev.
EOT
            ;;
        dev)
            cat <<EOT
Use the bmad-agent-dev skill.

Implement the stories from this session (or, if no stories were produced, implement the raw request below):

$PROMPT

Run pytest after each story. Do not skip tests. When done, state "ready for code review".
EOT
            ;;
        code-review)
            cat <<EOT
Use the bmad-code-review skill (acting as QA).

Review the diff produced in this session. Run pytest. If anything is broken or out of scope, file findings back to the Dev. Otherwise approve and state "approved".
EOT
            ;;
        *) echo "unknown persona: $1" >&2; exit 2 ;;
    esac
}

# --- 4. drive the chain ---------------------------------------------------
CLEAN_HOME="$(mktemp -d -t claude-bench-home-XXXXXX)"
trap 'rm -rf "$CLEAN_HOME"' EXIT

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
SID=""
n=0
for persona in "${CHAIN[@]}"; do
    n=$((n + 1))
    text="$(prompt_for "$persona")"
    echo "→ phase $n/${#CHAIN[@]}: $persona"
    if [[ -z "$SID" ]]; then
        SID="$(call_claude "$persona" "$n" "" "$text")"
        echo "  session: $SID"
    else
        call_claude "$persona" "$n" "$SID" "$text" >/dev/null
    fi
done

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

# --- 5. aggregate cost / tokens -------------------------------------------
TOTAL_COST=$(jq -s '[.[].total_cost_usd] | add' "$ART_DIR"/phase-*.json)
TOTAL_IN=$(jq -s '[.[].usage.input_tokens] | add' "$ART_DIR"/phase-*.json)
TOTAL_OUT=$(jq -s '[.[].usage.output_tokens] | add' "$ART_DIR"/phase-*.json)

# per-phase cost breakdown as a JSON array of {persona, cost}
PHASE_COSTS=$(
    for f in "$ART_DIR"/phase-*.json; do
        name=$(basename "$f" .json | sed 's/^phase-[0-9]*-//')
        cost=$(jq -r .total_cost_usd "$f")
        printf '{"persona":"%s","cost_usd":%s}\n' "$name" "$cost"
    done | jq -s '.'
)

# --- 6. snapshot BMAD artifacts -------------------------------------------
# BMAD writes planning + implementation artifacts under
# target/_bmad-output/. Snapshot them into the run artifact dir.
if [[ -d "$REPO_ROOT/target/_bmad-output" ]]; then
    rsync -a "$REPO_ROOT/target/_bmad-output/" "$ART_DIR/_bmad-output/" 2>/dev/null || \
        cp -R "$REPO_ROOT/target/_bmad-output" "$ART_DIR/_bmad-output"
fi

# --- 7. meta artifact -----------------------------------------------------
cat > "$ART_DIR/run-meta.json" <<EOF
{
  "workflow": "c",
  "task": $TASK,
  "run": $RUN,
  "label": "Scripted BMAD persona-chain replication",
  "branch": "$BRANCH",
  "base_branch": "$BASE",
  "prompt_hash": "$PROMPT_HASH",
  "session_id": "$SID",
  "model": "$MODEL",
  "hermetic_mode": true,
  "context_source": "target_only",
  "duration_seconds": $DURATION,
  "persona_chain": $(printf '"%s",' "${CHAIN[@]}" | sed 's/,$//' | awk '{print "[" $0 "]"}'),
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

Captured by harness/run_c_scripted.sh (BMAD ${#CHAIN[@]}-persona
chain). See results/runs/c-${TASK}-${RUN}/ on main for phase JSON
transcripts, _bmad-output/ snapshot, and run-meta.json." \
        >/dev/null
    echo "→ committed workflow edits on $BRANCH"
fi

# --- 8. record row --------------------------------------------------------
if [[ "$RECORD" == 0 ]]; then
    echo "--no-record set; skipping harness/run.py invocation."
    exit 0
fi

"$VENV_PY" "$REPO_ROOT/harness/run.py" \
    --workflow c --task "$TASK" --run "$RUN" \
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

# --- post-harness: park results on the workflow's base branch -----------
# Without this the operator has to manually stash, switch to main, pop,
# commit — and forgetting that order is how the C1 capture commit
# landed on the workflow branch the first time. We do it for them: stash
# the harness's results.csv update + the new artifact dir, switch back
# to the base branch, pop, leaving everything staged for one `git add &&
# git commit -m "..." on main / spec-kit-base / bmad-base`.
RESULT_STASH_REF=""
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain results/)" ]]; then
    git -C "$REPO_ROOT" stash push -u -m "scripted-runner: $BRANCH results/" -- results/ >/dev/null
    RESULT_STASH_REF="$(git -C "$REPO_ROOT" stash list | head -1 | cut -d: -f1)"
fi
git -C "$REPO_ROOT" checkout "$BASE" >/dev/null 2>&1
if [[ -n "$RESULT_STASH_REF" ]]; then
    git -C "$REPO_ROOT" stash pop "$RESULT_STASH_REF" >/dev/null
fi
echo "→ parked results/ changes on $BASE; commit them and you're done."
