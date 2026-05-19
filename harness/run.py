"""Benchmark run harness.

Wraps one benchmark run: checks out a fresh branch, pauses while the
operator runs the workflow manually, then captures git diff stats,
pytest results, wall-clock duration, token / cost numbers (entered by
the operator), and a 1-5 subjective score. Appends one row to
results/results.csv and saves artifacts to results/runs/.

Usage:
    python harness/run.py --workflow {a,b,c} --task {1,2,3,4} --run {1,2,3}
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
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
    "duration_seconds",
    "files_changed",
    "lines_added",
    "lines_removed",
    "tests_total",
    "tests_passed",
    "tokens_input",
    "tokens_output",
    "cost_usd",
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
    if not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0:
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


def collect_diff_stats(branch: str, base: str) -> dict[str, int]:
    # Use a staged-ish view: include both committed (if any) and working
    # tree changes relative to the workflow's base branch.
    output = subprocess.run(
        ["git", "diff", f"{base}...HEAD", "--numstat"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout
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
            files.add(path)
            if a.isdigit():
                added += int(a)
            if r.isdigit():
                removed += int(r)

    for path in untracked.splitlines():
        if path:
            files.add(path)

    return {
        "files_changed": len(files),
        "lines_added": added,
        "lines_removed": removed,
    }


def save_diff_artifact(artifact_dir: Path, base: str) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    committed = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, choices=["a", "b", "c"])
    parser.add_argument("--task", required=True, type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--run", required=True, type=int, choices=[1, 2, 3])
    args = parser.parse_args()

    confirm_clean_tree()
    ensure_csv_header()
    reset_target_db()

    branch = checkout_run_branch(args.workflow, args.task, args.run)
    print(f"Checked out {branch}")

    start = dt.datetime.now(tz=dt.timezone.utc)
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

    base = WORKFLOW_BASE_BRANCHES[args.workflow]
    print()
    print(f"Capturing diff (vs {base})…")
    save_diff_artifact(artifact_dir, base)
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

    print()
    print("Now grab token and cost numbers from the workflow:")
    print("  - A: /cost in Claude Code")
    print("  - B: sum across the five /speckit.* phases")
    print("  - C: /cost in Claude Code (aggregates across personas)")
    tokens_in = prompt_int("tokens_input")
    tokens_out = prompt_int("tokens_output")
    cost_usd = prompt_float("cost_usd")

    score = prompt_score()
    notes = prompt("Notes (one sentence — what defined the score)")

    row = {
        "timestamp": end.isoformat(timespec="seconds"),
        "workflow": args.workflow,
        "task": args.task,
        "run": args.run,
        "duration_seconds": int(duration),
        "files_changed": diff_stats["files_changed"],
        "lines_added": diff_stats["lines_added"],
        "lines_removed": diff_stats["lines_removed"],
        "tests_total": pytest_stats["tests_total"],
        "tests_passed": pytest_stats["tests_passed"],
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "cost_usd": cost_usd,
        "subjective_score": score,
        "notes": notes,
    }

    with RESULTS_CSV.open("a", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(row)

    (artifact_dir / "summary.json").write_text(json.dumps(row, indent=2))

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
