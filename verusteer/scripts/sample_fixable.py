"""Draw the 30-task comparison sample: failing test trees that a proof-only repair could fix.

Pool: test trees where the default rule and VeruSteer both fail and no recorded trajectory
verifies, classified by frozen_check.py as compile-fixable (errors only in editable code, not
flagged uncertain) or proof-only (the program compiles; its contract may still be false). Draws
10 compile-fixable and 5 proof-only trees per pipeline, at most one tree per task.

    python3 -I sample_fixable.py <VeruSteer repo> runs/frozen/frozen_check.csv runs/sample-30.csv
"""
from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
SEED = 30
QUOTA = {("compile-fixable", "autoverus"): 10, ("compile-fixable", "verusage"): 10,
         ("proof-only", "autoverus"): 5, ("proof-only", "verusage"): 5}


def bucket(frozen: dict) -> str | None:
    if frozen["uncertain"]:
        return None
    if frozen["status"] in ("only ghost code broken", "spec fn broken (editable)"):
        return "compile-fixable"
    return "proof-only" if frozen["status"] == "root compiles" else None


def main() -> None:
    repo, frozen_csv, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    frozen = {r["tree_id"]: r for r in csv.DictReader(frozen_csv.open())}
    verified_any = defaultdict(bool)
    for pipeline in ("autoverus", "verusage"):
        for line in (repo / f"data/paths/test_{pipeline}.jsonl").open():
            r = json.loads(line)
            verified_any[r["tree_id"]] |= r["label"]
    trees = [r for r in csv.DictReader((HERE / "test_trees.csv").open())
             if r["default_verified"] == "False" and r["steer_verified"] == "False"]
    pool = [r | {"bucket": bucket(frozen[r["tree_id"]])} for r in trees
            if bucket(frozen[r["tree_id"]]) and not verified_any[r["tree_id"]]]
    rng, picked, tasks, quota = random.Random(SEED), [], set(), dict(QUOTA)
    for r in rng.sample(pool, len(pool)):
        key = (r["bucket"], r["pipeline"])
        if quota.get(key, 0) and r["task_id"] not in tasks:
            picked.append(r)
            tasks.add(r["task_id"])
            quota[key] -= 1
    with out.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(picked[0]))
        writer.writeheader()
        writer.writerows(picked)
    print(f"pool {len(pool)}; sampled {len(picked)} -> {out}")


if __name__ == "__main__":
    main()
