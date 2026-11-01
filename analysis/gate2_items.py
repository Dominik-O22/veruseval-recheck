"""Gate 2 item lists: rejected per-clause L1/L2 lemmas from released records, keyed by sample ID.

    python3 -I analysis/gate2_items.py --release /work/release --repo . --out /work/items
Writes regrade14.jsonl (rejected L2 clauses of the 14 checker_wrong rows), devpool.jsonl (every
rejected L1/L2 clause on accepted artifacts of dev tasks) and dev100.jsonl (seeded sample of 100).
Only dev tasks and the 14 named rows are read.
"""
import argparse, csv, json, random
from pathlib import Path

SEED = 20261102
METRIC = {"L1": "precondition_clause_reliability_rate", "L2": "postcondition_clause_reliability_rate"}
COLUMN = {"L1": "pre_ref_to_gen", "L2": "post_gen_to_ref"}


def rejected(root, index, targets, sample, task, direction):
    record = json.loads((root / index[sample]).read_text())["metrics"][METRIC[direction]]["generated"]
    function = targets[task]
    out = []
    for f in record["functions"]:
        if f["function"] != function:
            continue
        for d in f["details"]:
            c = d.get("implication_check") or {}
            if c.get("status") == "invalid":
                out.append(c["obligation_context"]["check_name"])
    return out


def main():
    p = argparse.ArgumentParser(); p.add_argument("--release", type=Path); p.add_argument("--repo", type=Path)
    p.add_argument("--out", type=Path); a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    root = a.release
    with (root / "data/evaluation/artifact_index.csv").open() as s:
        index = {r["sample_id"]: r["result_path"] for r in csv.DictReader(s)}
    with (root / "data/evaluation/target_functions.csv").open() as s:
        targets = {r["task_id"]: r["target_function"] for r in csv.DictReader(s)}
    with (root / "data/evaluation/rq1_artifact_outcomes.csv").open() as s:
        outcomes = {r["sample_id"]: r for r in csv.DictReader(s)}
    def short(sample, d, check):
        return sample.replace("|", "__") + "__" + d + "__" + check.rsplit("_", 1)[-1]
    # 14 checker_wrong rows
    with (a.repo / "results/regrade-30/final_verdicts.csv").open() as s:
        rows = [r["sample_id"] for r in csv.DictReader(s) if r["verdict"] == "checker_wrong"]
    with (a.out / "regrade14.jsonl").open("w") as w:
        for sample in rows:
            task = outcomes[sample]["task_id"]
            for check in rejected(root, index, targets, sample, task, "L2"):
                w.write(json.dumps({"id": short(sample, "L2", check), "sample": sample, "task": task,
                                    "direction": "L2", "check": check}) + "\n")
    dev = set((a.repo / "results/tasks/dev_tasks.txt").read_text().split())
    pool = []
    for sample, r in sorted(outcomes.items()):
        if r["task_id"] not in dev or r["verification_stage"] != "accepted":
            continue
        for d in ("L1", "L2"):
            if r[COLUMN[d]] == "invalid":
                for check in rejected(root, index, targets, sample, r["task_id"], d):
                    pool.append({"id": short(sample, d, check), "sample": sample, "task": r["task_id"],
                                 "direction": d, "check": check})
    pool.sort(key=lambda x: x["id"])
    (a.out / "devpool.jsonl").write_text("".join(json.dumps(x) + "\n" for x in pool))
    pick = random.Random(SEED).sample(pool, 100)
    (a.out / "dev100.jsonl").write_text("".join(json.dumps(x) + "\n" for x in pick))
    from collections import Counter
    print("regrade14 clauses:", sum(1 for _ in open(a.out / "regrade14.jsonl")))
    print("dev pool:", len(pool), Counter(x["direction"] for x in pool), "tasks", len({x["task"] for x in pool}),
          "artifacts", len({x["sample"] for x in pool}))
    print("dev100:", Counter(x["direction"] for x in pick))


if __name__ == "__main__":
    main()
