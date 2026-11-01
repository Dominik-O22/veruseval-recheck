"""Does a check tend to fail larger contracts? Compares spec size within the same task, per check.

Tasks differ in difficulty and in natural contract size, so pooled rates by size mostly compare
tasks. Each row here counts the tasks where artifacts failing the check have a larger median spec
than those passing it, against the tasks where they have a smaller one.

    python3 -I analysis/size_by_check.py --release /path/to/veruseval-release
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
from typing import Callable

LEMMAS = {"L1": "pre_ref_to_gen", "L2": "post_gen_to_ref", "L3": "pre_gen_to_ref", "L4": "post_ref_to_gen"}
SUITES = {"correct-output suite": "io_correct_state", "wrong-output suite": "io_wrong_state",
          "invalid-input suite": "io_invalid_state"}


def load(release: Path) -> list[dict]:
    with (release / "data/evaluation/artifact_index.csv").open() as stream:
        paths = {r["sample_id"]: r["result_path"] for r in csv.DictReader(stream)}
    with (release / "data/evaluation/rq1_artifact_outcomes.csv").open() as stream:
        outcomes = {r["sample_id"]: r for r in csv.DictReader(stream)}
    rows = []
    with (release / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        for label in csv.DictReader(stream):
            if label["verification_stage"] != "accepted":
                continue
            result = json.loads((release / paths[label["sample_id"]]).read_text())
            size = ((result["metrics"].get("spec_size_complexity_spec_only") or {}).get("gen") or {}).get("node_count")
            if size is not None:
                rows.append({**label, **outcomes[label["sample_id"]], "size": size})
    return rows


def compare(rows: list[dict], name: str, failed: Callable[[dict], bool], scored: Callable[[dict], bool]) -> None:
    by_task: dict[str, dict[bool, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if scored(row):
            by_task[row["task_id"]][failed(row)].append(row["size"])
    larger = smaller = ties = 0
    ratios = []
    for groups in by_task.values():
        if groups[True] and groups[False]:
            fail, passed = statistics.median(groups[True]), statistics.median(groups[False])
            larger += fail > passed
            smaller += fail < passed
            ties += fail == passed
            if passed:
                ratios.append(fail / passed)
    n = larger + smaller
    z = (larger - n / 2) / math.sqrt(n / 4) if n else 0.0
    print(f"{name:<24} larger {larger:>3}  smaller {smaller:>3}  ties {ties:>2}  z {z:>5.1f}  "
          f"median ratio {statistics.median(ratios) if ratios else 0:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("."))
    args = parser.parse_args()
    rows = load(args.release)
    for name, column in LEMMAS.items():
        compare(rows, name, lambda r, c=column: r[c] == "invalid", lambda r, c=column: r[c] in ("valid", "invalid"))
    for name, column in SUITES.items():
        compare(rows, name, lambda r, c=column: r[c] == "unfavorable",
                lambda r, c=column: r[c] in ("favorable", "unfavorable"))


if __name__ == "__main__":
    main()
