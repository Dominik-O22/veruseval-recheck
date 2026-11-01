"""Rebuild results/tasks/tasks_fair20.csv from the release's labels and report each filter.

The pool is StarVerus few-shot tasks with an eligible artifact from all three strong models, minus
the broken-task list and the tasks already run, and minus any task a strong model scored clean on.
See docs/fair20-task-set.md for what that does and does not guarantee.

    python3 analysis/sample_fair20.py --release /path/to/veruseval-release --tasks results/tasks
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path
import random

SEED = 20261026
STRONG = {"deepseek-reasoner", "deepseek-chat", "qwen-coder"}
CHECKS = ("triviality_state", "io_state", "formal_state")


def clean(row: dict) -> bool:
    return row["verification_stage"] == "accepted" and all(row[k] == "favorable" for k in CHECKS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("."))
    parser.add_argument("--tasks", type=Path, default=Path("results/tasks"))
    args = parser.parse_args()

    with (args.release / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        rows = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True"
                and r["workflow"] == "StarVerus" and r["shot"] == "few-shot" and r["model"] in STRONG]
    by_task: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["model"]] = row
    complete = {t for t, models in by_task.items() if len(models) == 3}

    broken = set((args.tasks / "broken_tasks.txt").read_text().split())
    # The five tasks of tasks.csv already run in haiku-5, plus haiku-hard-1.
    with (args.tasks / "tasks.csv").open() as stream:
        used = {r["task_id"] for r in list(csv.DictReader(stream))[:5]} | {"HumanEval-Verus_task_6"}

    candidates = complete - broken - used
    pool = sorted(t for t in candidates if not any(clean(r) for r in by_task[t].values()))
    picked = random.Random(SEED).sample(pool, 20)

    print(f"all three strong models eligible: {len(complete)}")
    print(f"minus broken: {len(complete - broken)}")
    print(f"minus already run: {len(candidates)}")
    print(f"minus tasks a strong model scored clean on: {len(pool)}")
    with (args.tasks / "tasks_fair20.csv").open() as stream:
        recorded = [r["task_id"] for r in csv.DictReader(stream)]
    print(f"sample with seed {SEED} matches tasks_fair20.csv: {picked == recorded}")
    verified = Counter(sum(r["verification_stage"] == "accepted" for r in by_task[t].values()) for t in picked)
    print(f"strong models that verified each picked task: {dict(sorted(verified.items()))}")


if __name__ == "__main__":
    main()
