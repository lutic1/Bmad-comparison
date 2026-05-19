"""Re-score an existing run.

Useful if you want to look back at a saved diff and adjust a score
after the fact. Updates the row in results/results.csv in place.

Usage:
    python harness/score.py --workflow a --task 1 --run 1
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV = REPO_ROOT / "results" / "results.csv"
RUNS_DIR = REPO_ROOT / "results" / "runs"


def show_diff(artifact_dir: Path) -> None:
    for name in ("committed.diff", "working.diff"):
        path = artifact_dir / name
        if path.exists() and path.stat().st_size:
            print(f"---- {name} ----")
            print(path.read_text())


def prompt_score() -> int:
    print()
    print("Score this run on the 1-5 rubric (rubric/scoring-rubric.md):")
    print("  5 = merge as-is")
    print("  4 = merge after trivial review comments")
    print("  3 = request changes")
    print("  2 = significant rework needed")
    print("  1 = reject")
    while True:
        raw = input("Subjective score: ").strip()
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

    if not RESULTS_CSV.exists():
        sys.stderr.write("results.csv does not exist yet.\n")
        return 1

    artifact_dir = RUNS_DIR / f"{args.workflow}-{args.task}-{args.run}"
    if artifact_dir.exists():
        show_diff(artifact_dir)

    rows = list(csv.DictReader(RESULTS_CSV.open()))
    matched = [
        i
        for i, r in enumerate(rows)
        if r["workflow"] == args.workflow
        and int(r["task"]) == args.task
        and int(r["run"]) == args.run
    ]
    if not matched:
        sys.stderr.write(
            f"No row found for {args.workflow}/{args.task}/{args.run}\n"
        )
        return 1
    idx = matched[-1]
    print()
    print(f"Current score: {rows[idx]['subjective_score']}")
    print(f"Current notes: {rows[idx]['notes']}")
    new_score = prompt_score()
    new_notes = input("Notes (blank to keep existing): ").strip()
    rows[idx]["subjective_score"] = str(new_score)
    if new_notes:
        rows[idx]["notes"] = new_notes

    with RESULTS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("Updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
