#!/usr/bin/env bash
# Scripted Plan Mode replication for Workflow A.
#
# Drives one benchmark cell end-to-end without a human in the loop:
#   1. checks the working tree is clean, checks out workflow-a/task-N/run-M
#      off main, copies the project guardrails CLAUDE.md into target/,
#      resets target/app.db
#   2. extracts the task prompt body from tasks/0N-*.md
#   3. invokes `claude --print --permission-mode plan` against target/
#      and captures the plan, session_id, and cost JSON
#   4. resumes that session with --permission-mode acceptEdits, asking
#      Claude to execute the approved plan; captures the second call's
#      cost JSON
#   5. saves plan.md, plan-call.json, execute-call.json, and a small
#      run-meta.json under results/runs/a-N-M/
#   6. invokes harness/run.py --non-interactive --skip-branch with the
#      captured numeric values; the operator (or a follow-up step) fills
#      in subjective score and notes via --score / --notes
#
# All claude invocations use --bare --model sonnet --add-dir target so
# the run is isolated from the operator's global Claude Code config and
# uses a typical, economically-realistic model.
#
# Usage:
#   harness/run_a_scripted.sh --task N --run M \
#       --score INT --notes "one sentence"
#
# Pass --no-record to skip the harness/run.py call (useful for dry
# runs and inspection).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TASK=""
RUN=""
SCORE=""
NOTES=""
RECORD=1
MODEL="sonnet"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task) TASK="$2"; shift 2 ;;
        --run) RUN="$2"; shift 2 ;;
        --score) SCORE="$2"; shift 2 ;;
        --notes) NOTES="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --no-record) RECORD=0; shift ;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

[[ -z "$TASK" || -z "$RUN" ]] && {
    echo "missing --task / --run" >&2
    exit 2
}
[[ "$TASK" =~ ^[1-4]$ ]] || { echo "--task must be 1..4" >&2; exit 2; }
[[ "$RUN" =~ ^[1-3]$ ]] || { echo "--run must be 1..3" >&2; exit 2; }
if [[ "$RECORD" == 1 && ( -z "$SCORE" || -z "$NOTES" ) ]]; then
    echo "--score and --notes required unless --no-record" >&2
    exit 2
fi

VENV_PY="$REPO_ROOT/target/.venv/bin/python"
[[ -x "$VENV_PY" ]] || {
    echo "venv python not found at $VENV_PY — run pip install -e .[dev] first" >&2
    exit 2
}

TASK_FILE_NAMES=( [1]=01-trivial.md [2]=02-medium.md [3]=03-ambiguous.md [4]=04-brownfield.md )
TASK_FILE="$REPO_ROOT/tasks/${TASK_FILE_NAMES[$TASK]}"
[[ -f "$TASK_FILE" ]] || { echo "task file missing: $TASK_FILE" >&2; exit 2; }

BRANCH="workflow-a/task-${TASK}/run-${RUN}"
BASE="main"
ART_DIR="$REPO_ROOT/results/runs/a-${TASK}-${RUN}"
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
# everything between "## Prompt" and the next "## " heading; trim.
PROMPT="$(awk '
    /^## Prompt/ { capture=1; next }
    capture && /^## / { exit }
    capture { print }
' "$TASK_FILE" | sed -e '/./,$!d' -e :a -e '/^\n*$/{$d;N;ba' -e '}')"
[[ -z "$PROMPT" ]] && { echo "could not extract prompt from $TASK_FILE" >&2; exit 2; }
PROMPT_HASH="sha256:$(printf '%s' "$PROMPT" | shasum -a 256 | awk '{print $1}')"

# --- 3. plan call ---------------------------------------------------------
START_TS=$(date +%s)
echo "→ plan call (claude -p --permission-mode plan, --bare --model $MODEL)"
PLAN_JSON_PATH="$ART_DIR/plan-call.json"
(
    cd "$REPO_ROOT/target"
    claude --print \
        --bare \
        --model "$MODEL" \
        --add-dir "$REPO_ROOT/target" \
        --permission-mode plan \
        --output-format json \
        "$PROMPT" > "$PLAN_JSON_PATH"
)

SESSION_ID="$(jq -r .session_id "$PLAN_JSON_PATH")"
PLAN_COST="$(jq -r .total_cost_usd "$PLAN_JSON_PATH")"
PLAN_IN="$(jq -r .usage.input_tokens "$PLAN_JSON_PATH")"
PLAN_OUT="$(jq -r .usage.output_tokens "$PLAN_JSON_PATH")"

# The plan body lives in permission_denials[].tool_input.plan when
# ExitPlanMode was denied (Plan Mode never auto-approves). Claude also
# writes a slugged copy to ~/.claude/plans/<slug>.md; capture both for
# triangulation.
PLAN_BODY="$(jq -r '
    .permission_denials
    | map(select(.tool_name == "ExitPlanMode"))
    | (last // {}).tool_input.plan // ""
' "$PLAN_JSON_PATH")"
PLAN_PATH_HINT="$(jq -r '
    .permission_denials
    | map(select(.tool_name == "ExitPlanMode"))
    | (last // {}).tool_input.planFilePath // ""
' "$PLAN_JSON_PATH")"

if [[ -n "$PLAN_BODY" ]]; then
    printf '%s\n' "$PLAN_BODY" > "$ART_DIR/plan.md"
elif [[ -n "$PLAN_PATH_HINT" && -f "$PLAN_PATH_HINT" ]]; then
    cp "$PLAN_PATH_HINT" "$ART_DIR/plan.md"
else
    echo "WARNING: could not extract plan body; saving empty plan.md" >&2
    : > "$ART_DIR/plan.md"
fi

echo "  session: $SESSION_ID"
echo "  plan cost: \$$PLAN_COST  in:$PLAN_IN out:$PLAN_OUT"

# --- 4. execute call ------------------------------------------------------
echo "→ execute call (claude -p --resume --permission-mode acceptEdits)"
EXEC_JSON_PATH="$ART_DIR/execute-call.json"
(
    cd "$REPO_ROOT/target"
    claude --print \
        --bare \
        --model "$MODEL" \
        --add-dir "$REPO_ROOT/target" \
        --resume "$SESSION_ID" \
        --permission-mode acceptEdits \
        --output-format json \
        "Approved. Proceed with the plan exactly as written. Run pytest at the end; the run is only complete when tests pass." \
        > "$EXEC_JSON_PATH"
)

EXEC_COST="$(jq -r .total_cost_usd "$EXEC_JSON_PATH")"
EXEC_IN="$(jq -r .usage.input_tokens "$EXEC_JSON_PATH")"
EXEC_OUT="$(jq -r .usage.output_tokens "$EXEC_JSON_PATH")"
echo "  exec cost: \$$EXEC_COST  in:$EXEC_IN out:$EXEC_OUT"

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

# --- 5. meta artifact -----------------------------------------------------
TOTAL_COST=$(python3 -c "print(round($PLAN_COST + $EXEC_COST, 6))")
TOTAL_IN=$((PLAN_IN + EXEC_IN))
TOTAL_OUT=$((PLAN_OUT + EXEC_OUT))

cat > "$ART_DIR/run-meta.json" <<EOF
{
  "workflow": "a",
  "task": $TASK,
  "run": $RUN,
  "label": "Scripted Plan Mode replication",
  "branch": "$BRANCH",
  "base_branch": "$BASE",
  "prompt_hash": "$PROMPT_HASH",
  "session_id": "$SESSION_ID",
  "model": "$MODEL",
  "bare_mode": true,
  "context_source": "target_only",
  "duration_seconds": $DURATION,
  "plan_call_cost_usd": $PLAN_COST,
  "plan_call_tokens_input": $PLAN_IN,
  "plan_call_tokens_output": $PLAN_OUT,
  "execute_call_cost_usd": $EXEC_COST,
  "execute_call_tokens_input": $EXEC_IN,
  "execute_call_tokens_output": $EXEC_OUT,
  "total_cost_usd": $TOTAL_COST,
  "total_tokens_input": $TOTAL_IN,
  "total_tokens_output": $TOTAL_OUT
}
EOF

echo
echo "captured: $(ls "$ART_DIR" | tr '\n' ' ')"
echo "duration: ${DURATION}s   total cost: \$${TOTAL_COST}"

# --- 6. record row --------------------------------------------------------
if [[ "$RECORD" == 0 ]]; then
    echo "--no-record set; skipping harness/run.py invocation."
    echo "Branch $BRANCH retained for inspection."
    exit 0
fi

"$VENV_PY" "$REPO_ROOT/harness/run.py" \
    --workflow a --task "$TASK" --run "$RUN" \
    --non-interactive --skip-branch \
    --duration-seconds "$DURATION" \
    --prompt-hash "$PROMPT_HASH" \
    --plan-cost-usd "$PLAN_COST" \
    --plan-tokens-input "$PLAN_IN" \
    --plan-tokens-output "$PLAN_OUT" \
    --execute-cost-usd "$EXEC_COST" \
    --execute-tokens-input "$EXEC_IN" \
    --execute-tokens-output "$EXEC_OUT" \
    --total-cost-usd "$TOTAL_COST" \
    --total-tokens-input "$TOTAL_IN" \
    --total-tokens-output "$TOTAL_OUT" \
    --model "$MODEL" \
    --bare-mode true \
    --context-source target_only \
    --score "$SCORE" \
    --notes "$NOTES"
