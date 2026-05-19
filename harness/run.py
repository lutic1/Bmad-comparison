"""Benchmark run harness.

Wraps one benchmark run: checks out a fresh branch off the workflow's
base, optionally pauses for an interactive operator session (default
mode) or accepts every captured value as a flag (--non-interactive),
captures git diff stats, pytest results, wall-clock duration, token /
cost numbers, and a 1-5 subjective score. Appends one row to
results/results.csv and saves artifacts to results/runs/.

Usage:
    # interactive (original behaviour)
    python harness/run.py --workflow {a,b,c} --task {1,2,3,4} --run {1,2,3}

    # non-interactive (driven by harness/run_a_scripted.sh et al.)
    python harness/run.py --workflow a --task 1 --run 1 --non-interactive \\
        --duration-seconds 134 \\
        --plan-cost-usd 0.41 --plan-tokens-input 12345 --plan-tokens-output 678 \\
        --execute-cost-usd 0.22 --execute-tokens-input 5678 --execute-tokens-output 234 \\
        --prompt-hash sha256:abcd... \\
        --model sonnet --hermetic-mode true --context-source target_only \\
        --score 4 --notes "happy-path, no scope creep"
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = REPO_ROOT / "target"
RESULTS_CSV = REPO_ROOT / "results" / "results.csv"
RUNS_DIR = REPO_ROOT / "results" / "runs"
TASKS_DIR = REPO_ROOT / "tasks"
WORKFLOWS_DIR = REPO_ROOT / "workflows"

CSV_COLUMNS = [
    "timestamp",
    "workflow",
    "task",
    "run",
    "base_branch",
    "branch_name",
    "prompt_hash",
    "duration_seconds",
    "files_changed",
    "lines_added",
    "lines_removed",
    "tests_total",
    "tests_passed",
    "plan_call_cost_usd",
    "plan_call_tokens_input",
    "plan_call_tokens_output",
    "execute_call_cost_usd",
    "execute_call_tokens_input",
    "execute_call_tokens_output",
    "tokens_input",
    "tokens_output",
    "cost_usd",
    "model",
    "hermetic_mode",
    "context_source",
    "subjective_score",
    "notes",
]

TASK_FILES = {
    1: "01-trivial.md",
    2: "02-medium.md",
    3: "03-ambiguous.md",
    4: "04-brownfield.md",
}

WORKFLOW_RUNBOOKS = {
    "a": "a-plan-mode.md",
    "b": "b-spec-kit.md",
    "c": "c-bmad.md",
}

# Each workflow branches off a different base so framework files don't
# contaminate the other workflows. See README → Repository layout.
WORKFLOW_BASE_BRANCHES = {
    "a": "main",
    "b": "spec-kit-base",
    "c": "bmad-base",
}


def run_git(*args: str, cwd: Path = REPO_ROOT, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True
    )
    return result.stdout.strip()


def ensure_csv_header() -> None:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    needs_header = (
        not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0
    )
    if not needs_header:
        # Detect old single-totals schema and migrate by rewriting header.
        with RESULTS_CSV.open() as f:
            first = f.readline().strip().split(",")
        if first != CSV_COLUMNS:
            backup = RESULTS_CSV.with_suffix(".csv.bak")
            RESULTS_CSV.rename(backup)
            sys.stderr.write(
                f"results.csv schema changed; old file moved to "
                f"{backup.name}.\n"
            )
            needs_header = True
    if needs_header:
        with RESULTS_CSV.open("w", newline="") as f:
            csv.writer(f).writerow(CSV_COLUMNS)


def confirm_clean_tree() -> None:
    status = run_git("status", "--porcelain")
    if status:
        sys.stderr.write(
            "Working tree is not clean. Commit or stash before running.\n"
            f"{status}\n"
        )
        sys.exit(1)


def checkout_run_branch(workflow: str, task: int, run: int) -> str:
    branch = f"workflow-{workflow}/task-{task}/run-{run}"
    base = WORKFLOW_BASE_BRANCHES[workflow]
    run_git("checkout", base)
    # Delete the branch locally if it exists from a previous attempt.
    existing = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0:
        sys.stderr.write(
            f"Branch {branch} already exists locally. Delete it first if "
            f"you really mean to overwrite the run.\n"
        )
        sys.exit(1)
    run_git("checkout", "-b", branch)
    return branch


def reset_target_db() -> None:
    db = TARGET_DIR / "app.db"
    if db.exists():
        db.unlink()


def print_workflow_prompt(workflow: str, task: int) -> None:
    runbook = WORKFLOWS_DIR / WORKFLOW_RUNBOOKS[workflow]
    task_file = TASKS_DIR / TASK_FILES[task]
    print()
    print("=" * 72)
    print(f"Workflow: {workflow.upper()}   Task: {task}")
    print("=" * 72)
    print(f"Runbook:  {runbook.relative_to(REPO_ROOT)}")
    print(f"Task:     {task_file.relative_to(REPO_ROOT)}")
    print()
    print("Follow the runbook in another shell. The harness is waiting.")
    print("Do NOT commit any changes yet — let the harness capture the diff.")
    print()


def _is_workflow_path(path: str) -> bool:
    """A diff entry counts as workflow output only if the workflow
    actually produced it. Excludes:
      - the guardrails CLAUDE.md the runbook copies into target/
      - any harness artifact under results/
      - anything outside target/ (e.g. the operator editing a runbook
        mid-run)
    """
    if not path.startswith("target/"):
        return False
    if path == "target/CLAUDE.md":
        return False
    return True


def collect_diff_stats(branch: str, base: str) -> dict[str, int]:
    # Three-dot diff between base and the workflow branch's tip — works
    # whether HEAD is on the workflow branch or any other branch (e.g.
    # the operator has returned to base for inspection).
    output = subprocess.run(
        ["git", "diff", f"{base}...{branch}", "--numstat"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout
    # Working-tree diff only matters if HEAD == branch.
    head = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    working = ""
    untracked = ""
    if head == branch:
        working = subprocess.run(
            ["git", "diff", "HEAD", "--numstat"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout

    files: set[str] = set()
    added = 0
    removed = 0

    for block in (output, working):
        for line in block.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            a, r, path = parts[0], parts[1], parts[2]
            if not _is_workflow_path(path):
                continue
            files.add(path)
            if a.isdigit():
                added += int(a)
            if r.isdigit():
                removed += int(r)

    for path in untracked.splitlines():
        if path and _is_workflow_path(path):
            files.add(path)

    return {
        "files_changed": len(files),
        "lines_added": added,
        "lines_removed": removed,
    }


def save_diff_artifact(artifact_dir: Path, base: str, branch: str) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    committed = subprocess.run(
        ["git", "diff", f"{base}...{branch}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout
    head = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    working = ""
    if head == branch:
        working = subprocess.run(
            ["git", "diff", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout
    (artifact_dir / "committed.diff").write_text(committed)
    (artifact_dir / "working.diff").write_text(working)


def run_pytest(artifact_dir: Path) -> dict[str, int]:
    report_path = artifact_dir / "pytest-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--json-report",
            f"--json-report-file={report_path}",
            "-q",
        ],
        cwd=TARGET_DIR,
        capture_output=True,
        text=True,
    )
    (artifact_dir / "pytest-stdout.txt").write_text(result.stdout)
    (artifact_dir / "pytest-stderr.txt").write_text(result.stderr)

    total = 0
    passed = 0
    if report_path.exists():
        try:
            data = json.loads(report_path.read_text())
            summary = data.get("summary", {})
            total = int(summary.get("total", 0))
            passed = int(summary.get("passed", 0))
        except json.JSONDecodeError:
            pass

    return {"tests_total": total, "tests_passed": passed}


def prompt(prompt_text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{prompt_text}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def prompt_int(prompt_text: str, default: int = 0) -> int:
    while True:
        raw = prompt(prompt_text, str(default))
        try:
            return int(raw)
        except ValueError:
            print("  please enter an integer")


def prompt_float(prompt_text: str, default: float = 0.0) -> float:
    while True:
        raw = prompt(prompt_text, str(default))
        try:
            return float(raw)
        except ValueError:
            print("  please enter a number")


def prompt_score() -> int:
    print()
    print("Score this run on the 1-5 rubric (rubric/scoring-rubric.md):")
    print("  5 = merge as-is")
    print("  4 = merge after trivial review comments")
    print("  3 = request changes")
    print("  2 = significant rework needed")
    print("  1 = reject")
    while True:
        raw = prompt("Subjective score")
        try:
            n = int(raw)
            if 1 <= n <= 5:
                return n
        except ValueError:
            pass
        print("  please enter an integer 1-5")


def parse_bool(s: str) -> bool:
    return s.lower() in ("true", "1", "yes", "y")


def append_row(row: dict, artifact_dir: Path) -> None:
    ensure_csv_header()
    with RESULTS_CSV.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(row)
    (artifact_dir / "summary.json").write_text(json.dumps(row, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, choices=["a", "b", "c"])
    parser.add_argument("--task", required=True, type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--run", required=True, type=int, choices=[1, 2, 3])

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive prompts; require all values as flags.",
    )
    parser.add_argument(
        "--skip-branch",
        action="store_true",
        help=(
            "Do not check out a new branch. Use when an upstream script "
            "(e.g. run_a_scripted.sh) already created the branch."
        ),
    )
    parser.add_argument(
        "--branch-name",
        type=str,
        default="",
        help=(
            "Override the branch-name HEAD check. When set with "
            "--skip-branch, the harness records the supplied name as "
            "branch_name without requiring HEAD to match — and computes "
            "diff stats against the supplied branch instead of HEAD. "
            "Use when the operator has already returned to the base "
            "branch for inspection."
        ),
    )
    # Non-interactive value flags.
    parser.add_argument("--duration-seconds", type=int)
    parser.add_argument("--prompt-hash", type=str, default="")
    parser.add_argument("--plan-cost-usd", type=float, default=0.0)
    parser.add_argument("--plan-tokens-input", type=int, default=0)
    parser.add_argument("--plan-tokens-output", type=int, default=0)
    parser.add_argument("--execute-cost-usd", type=float, default=0.0)
    parser.add_argument("--execute-tokens-input", type=int, default=0)
    parser.add_argument("--execute-tokens-output", type=int, default=0)
    parser.add_argument(
        "--total-cost-usd",
        type=float,
        help=(
            "Total cost. If omitted, computed as plan + execute (workflow A) "
            "or required for B/C."
        ),
    )
    parser.add_argument("--total-tokens-input", type=int)
    parser.add_argument("--total-tokens-output", type=int)
    parser.add_argument("--model", type=str, default="")
    parser.add_argument("--hermetic-mode", type=str, default="")
    parser.add_argument("--context-source", type=str, default="")
    parser.add_argument("--score", type=int)
    parser.add_argument("--notes", type=str, default="")

    args = parser.parse_args()

    if not args.skip_branch:
        confirm_clean_tree()
    ensure_csv_header()
    reset_target_db()

    base = WORKFLOW_BASE_BRANCHES[args.workflow]
    if args.skip_branch:
        head = run_git("rev-parse", "--abbrev-ref", "HEAD")
        expected = f"workflow-{args.workflow}/task-{args.task}/run-{args.run}"
        if args.branch_name:
            branch = args.branch_name
            # Verify the branch exists so diff stats can be computed.
            rev = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if rev.returncode != 0:
                sys.stderr.write(
                    f"--branch-name {branch} does not exist as a git ref.\n"
                )
                return 2
        elif head != expected:
            sys.stderr.write(
                f"--skip-branch set but HEAD is {head}, expected "
                f"{expected}. Pass --branch-name {expected} to record "
                f"from a different HEAD.\n"
            )
            return 2
        else:
            branch = head
    else:
        branch = checkout_run_branch(args.workflow, args.task, args.run)
        print(f"Checked out {branch}")

    start = dt.datetime.now(tz=dt.timezone.utc)

    if args.non_interactive:
        if args.duration_seconds is None or args.score is None:
            sys.stderr.write(
                "--non-interactive requires --duration-seconds and --score.\n"
            )
            return 2
        duration = float(args.duration_seconds)
        end = start + dt.timedelta(seconds=duration)
    else:
        print_workflow_prompt(args.workflow, args.task)
        while True:
            done = prompt("Type 'y' when the workflow is complete (or 'abort')")
            if done.lower() == "abort":
                print("Aborted. Branch left in place for inspection.")
                return 1
            if done.lower() in ("y", "yes"):
                break
        end = dt.datetime.now(tz=dt.timezone.utc)
        duration = (end - start).total_seconds()

    artifact_dir = RUNS_DIR / f"{args.workflow}-{args.task}-{args.run}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Capturing diff ({base}...{branch})…")
    save_diff_artifact(artifact_dir, base, branch)
    diff_stats = collect_diff_stats(branch, base)
    print(
        f"  files changed: {diff_stats['files_changed']}"
        f"   +{diff_stats['lines_added']} -{diff_stats['lines_removed']}"
    )

    print("Running pytest…")
    pytest_stats = run_pytest(artifact_dir)
    print(
        f"  tests: {pytest_stats['tests_passed']} / {pytest_stats['tests_total']} passed"
    )

    if args.non_interactive:
        plan_cost = args.plan_cost_usd
        plan_in = args.plan_tokens_input
        plan_out = args.plan_tokens_output
        exec_cost = args.execute_cost_usd
        exec_in = args.execute_tokens_input
        exec_out = args.execute_tokens_output
        total_cost = (
            args.total_cost_usd
            if args.total_cost_usd is not None
            else plan_cost + exec_cost
        )
        total_in = (
            args.total_tokens_input
            if args.total_tokens_input is not None
            else plan_in + exec_in
        )
        total_out = (
            args.total_tokens_output
            if args.total_tokens_output is not None
            else plan_out + exec_out
        )
        score = args.score
        notes = args.notes
        model = args.model
        hermetic_mode = args.hermetic_mode
        context_source = args.context_source
        prompt_hash = args.prompt_hash
    else:
        print()
        print("Now grab token and cost numbers from the workflow:")
        print("  - A: /cost in Claude Code")
        print("  - B: sum across the five /speckit.* phases")
        print("  - C: /cost in Claude Code (aggregates across personas)")
        total_in = prompt_int("tokens_input (total)")
        total_out = prompt_int("tokens_output (total)")
        total_cost = prompt_float("cost_usd (total)")
        plan_cost = plan_in = plan_out = 0.0
        exec_cost = exec_in = exec_out = 0.0
        plan_cost = 0.0
        score = prompt_score()
        notes = prompt("Notes (one sentence — what defined the score)")
        model = ""
        hermetic_mode = ""
        context_source = ""
        prompt_hash = ""

    row = {
        "timestamp": end.isoformat(timespec="seconds"),
        "workflow": args.workflow,
        "task": args.task,
        "run": args.run,
        "base_branch": base,
        "branch_name": branch,
        "prompt_hash": prompt_hash,
        "duration_seconds": int(duration),
        "files_changed": diff_stats["files_changed"],
        "lines_added": diff_stats["lines_added"],
        "lines_removed": diff_stats["lines_removed"],
        "tests_total": pytest_stats["tests_total"],
        "tests_passed": pytest_stats["tests_passed"],
        "plan_call_cost_usd": plan_cost,
        "plan_call_tokens_input": plan_in,
        "plan_call_tokens_output": plan_out,
        "execute_call_cost_usd": exec_cost,
        "execute_call_tokens_input": exec_in,
        "execute_call_tokens_output": exec_out,
        "tokens_input": total_in,
        "tokens_output": total_out,
        "cost_usd": total_cost,
        "model": model,
        "hermetic_mode": hermetic_mode,
        "context_source": context_source,
        "subjective_score": score,
        "notes": notes,
    }

    append_row(row, artifact_dir)

    print()
    print(f"Run captured: {RESULTS_CSV.relative_to(REPO_ROOT)}")
    print(f"Artifacts:    {artifact_dir.relative_to(REPO_ROOT)}")
    print()
    print("When you're ready for the next run:")
    print(f"  git checkout {base}")
    print(f"  # branch {branch} retained for diff inspection")
    return 0


if __name__ == "__main__":
    sys.exit(main())
