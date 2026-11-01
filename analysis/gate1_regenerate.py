"""Gate 1: can the release's per-clause L1 and L2 checks be regenerated?

Draws a seeded 20% development set of tasks with a rejected L1 or L2, samples artifacts from it,
re-runs the unpatched per-clause path, and compares each clause's obligation context and status
with the released record. No model calls. Stored hashes are not compared, because they depend on
absolute paths and the Verus binary.

Run inside the VerusEval container from the release root:
    python haiku/gate1_regenerate.py --per-direction 40 --out runs/gate1.jsonl
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from multiprocessing import Pool
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import metrics_rebuild.share.lemma_implication as li
from metrics_rebuild.share.functions import strength_contexts_for_path
from metrics_rebuild.share.smt import clause_implication_metric

SEED = 20261101
DIRECTIONS = {
    "L1": ("pre_ref_to_gen", "precondition_clause_reliability_rate",
           dict(source_side="generated", clause_kind="requires",
                implication_direction="reference_implies_generated_clause")),
    "L2": ("post_gen_to_ref", "postcondition_clause_reliability_rate",
           dict(source_side="reference", clause_kind="ensures",
                implication_direction="generated_implies_reference_clause")),
}
CONTEXT = ("function", "check_name", "antecedent", "consequent", "antecedent_kinds", "consequent_kinds")


def sample(per_direction: int) -> list[dict]:
    with (ROOT / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        accepted = {r["sample_id"]: r for r in csv.DictReader(stream) if r["verification_stage"] == "accepted"}
    with (ROOT / "data/evaluation/rq1_artifact_outcomes.csv").open() as stream:
        outcomes = [r for r in csv.DictReader(stream) if r["sample_id"] in accepted]
    tasks = sorted({accepted[r["sample_id"]]["task_id"] for r in outcomes
                    if "invalid" in (r["pre_ref_to_gen"], r["post_gen_to_ref"])})
    rng = random.Random(SEED)
    development = set(rng.sample(tasks, round(len(tasks) * 0.2)))
    picked = []
    for direction, (column, _, _) in DIRECTIONS.items():
        pool = sorted(r["sample_id"] for r in outcomes
                      if r[column] == "invalid" and accepted[r["sample_id"]]["task_id"] in development)
        picked += [{"sample": s, "direction": direction, "task": accepted[s]["task_id"]}
                   for s in rng.sample(pool, min(per_direction, len(pool)))]
    return picked


def compare(item: dict) -> list[dict]:
    li.set_lemma_verus_binary("/opt/verus/verus")
    with (ROOT / "data/evaluation/artifact_index.csv").open() as stream:
        result_path = next(r["result_path"] for r in csv.DictReader(stream) if r["sample_id"] == item["sample"])
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        target = next(r for r in csv.DictReader(stream) if r["task_id"] == item["task"])
    _, metric, arguments = DIRECTIONS[item["direction"]]
    record = json.loads((ROOT / result_path).read_text())["metrics"][metric]["generated"]
    released = next(f for f in record["functions"] if f["function"] == target["target_function"])
    generated = released["details"][0]["implication_check"]["obligation_context"]["generated_path"]
    reference = target["reference_path"]
    regenerated = clause_implication_metric(
        strength_contexts_for_path(generated), strength_contexts_for_path(reference),
        reference_rs_path=reference, metric_kind="x", note="x", generated_rs_path=generated, **arguments)
    mine = {d["implication_check"]["obligation_context"]["check_name"]: d["implication_check"]
            for f in regenerated["functions"] if f["function"] == target["target_function"] for d in f["details"]}
    rows = []
    for detail in released["details"]:
        check = detail["implication_check"]
        name = check["obligation_context"]["check_name"]
        other = mine.get(name)
        rows.append({**item, "check": name, "released": check["status"], "regenerated": other and other["status"],
                     "context_same": bool(other) and all(check["obligation_context"][k] == other["obligation_context"][k]
                                                         for k in CONTEXT)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-direction", type=int, default=40)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path, default=ROOT / "runs/gate1.jsonl")
    args = parser.parse_args()
    items = sample(args.per_direction)
    tally: Counter = Counter()
    with args.out.open("w") as stream, Pool(args.workers) as pool:
        for rows in pool.imap_unordered(compare, items):
            for row in rows:
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                tally[(row["direction"], row["context_same"], row["released"] == row["regenerated"])] += 1
    for (direction, context, status), n in sorted(tally.items()):
        print(f"{direction}\tcontext {'same' if context else 'differs'}\tstatus {'same' if status else 'differs'}\t{n}")


if __name__ == "__main__":
    main()
