"""Statistics recomputed from the paper's released RQ1 labels.

Reports the headline under a strict metric (all three semantic checks, formal
equivalence) and a reliability-only metric (the generated contract may be
stronger than the reference), with and without broken tasks; the share of
trivial specs; where verification failures stop; and a within-task size
comparison between failed and accepted artifacts.

    python analysis/released_labels.py --release /path/to/veruseval-release --tasks results/tasks
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path
import statistics

STRONG = {"deepseek-reasoner", "deepseek-chat", "qwen-coder"}
CHECKS = ("triviality_state", "io_state")


def favorable(row: dict, formal: str) -> bool:
    return all(row[k] == "favorable" for k in (*CHECKS, formal))


def headline(rows: list[dict], name: str) -> None:
    accepted = [r for r in rows if r["verification_stage"] == "accepted"]
    strict = sum(favorable(r, "formal_state") for r in accepted) / len(accepted)
    lenient = sum(favorable(r, "formal_reliability_state") for r in accepted) / len(accepted)
    print(f"  {name:<44}{len(accepted):>6} accepted   strict {strict:6.1%}   reliability-only {lenient:6.1%}")


def within_task(rows: list[dict], group_a, group_b, key: str, name: str) -> None:
    """Share of tasks where group A's mean `key` exceeds group B's."""
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    larger = smaller = 0
    for task_rows in by_task.values():
        a = [float(r[key]) for r in task_rows if group_a(r) and r[key]]
        b = [float(r[key]) for r in task_rows if group_b(r) and r[key]]
        if a and b and statistics.mean(a) != statistics.mean(b):
            larger += statistics.mean(a) > statistics.mean(b)
            smaller += statistics.mean(a) < statistics.mean(b)
    print(f"  {name:<58}{larger + smaller:>5} tasks   A larger in {larger / (larger + smaller):6.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("."))
    parser.add_argument("--tasks", type=Path, default=Path("results/tasks"))
    args = parser.parse_args()
    with (args.release / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        rows = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True"]
    broken = set((args.tasks / "broken_tasks.txt").read_text().split())

    print("Headline (accepted artifacts passing all semantic checks):")
    headline(rows, "all tasks (paper)")
    headline([r for r in rows if r["task_id"] not in broken], "minus broken tasks")
    headline([r for r in rows if r["task_id"] not in broken and r["model"] in STRONG],
             "minus broken tasks, strong models only")

    accepted = [r for r in rows if r["verification_stage"] == "accepted"]
    trivial = sum(r["triviality_state"] == "unfavorable" for r in accepted)
    print(f"\nTrivial specs: {trivial} of {len(accepted)} accepted ({trivial / len(accepted):.1%})")

    failed = [r for r in rows if r["verification_stage"] != "accepted"]
    stages = Counter(r["verification_stage"] for r in failed)
    print(f"\nWhere {len(failed)} verification failures stop:")
    for stage in ("parse_failed", "frontend_failed", "proof_failed"):
        print(f"  {stage:<16}{stages[stage]:>6}  {stages[stage] / len(failed):6.1%}")

    print("\nWithin-task size comparison (A vs B):")
    stage = lambda name: (lambda r: r["verification_stage"] == name)
    within_task(rows, stage("frontend_failed"), stage("accepted"), "spec_node_count",
                "spec size: frontend-failed (A) vs accepted (B)")
    within_task(rows, stage("proof_failed"), stage("accepted"), "proof_node_count",
                "proof size: proof-failed (A) vs accepted (B)")


if __name__ == "__main__":
    main()
