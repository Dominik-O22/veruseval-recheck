"""Summarize a run_haiku.py evaluation: per model, how many tasks were accepted by
Verus and how many of those passed all three semantic checks (non-trivial, I/O,
formal equivalence), using the release's own label extraction.

    python haiku/summarize.py runs/haiku-dry
"""
from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.rebuild_rq1_inputs import extract

CHECKS = ("triviality_state", "io_state", "formal_state")


def main() -> None:
    run = Path(sys.argv[1])
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        catalog = {r["task_id"]: r for r in csv.DictReader(stream)}
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # tasks, accepted, clean
    for path in sorted((run / "eval").rglob("per_file/*.json")):
        payload = json.loads(path.read_text())
        if not payload["target_evaluation"]["analysis_eligible"]:
            continue
        label, _ = extract(payload, path, catalog[payload["target_evaluation"]["sample_id"].split("|")[-1]])
        accepted = label["verification_stage"] == "accepted"
        row = stats[label["model"]]
        row[0] += 1
        row[1] += accepted
        row[2] += accepted and all(label[c] == "favorable" for c in CHECKS)
    print(f"{'model':<20}{'tasks':>6}{'accepted':>10}{'clean':>7}")
    for model, (tasks, accepted, clean) in sorted(stats.items()):
        print(f"{model:<20}{tasks:>6}{accepted:>10}{clean:>7}")
    usage = run / "usage.jsonl"
    if usage.exists():
        calls = [json.loads(line) for line in usage.read_text().splitlines()]
        tokens = lambda key: sum(c["usage"].get(key, 0) for c in calls)
        print(f"\nclaude calls: {len(calls)}, input {tokens('input_tokens') + tokens('cache_read_input_tokens') + tokens('cache_creation_input_tokens'):,}"
              f" tok, output {tokens('output_tokens'):,} tok, API-equivalent ${sum(c['total_cost_usd'] or 0 for c in calls):.2f}")


if __name__ == "__main__":
    main()
