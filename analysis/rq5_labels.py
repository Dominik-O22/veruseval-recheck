"""First-attempt L1 to L4 labels for a program, through the release's own per-clause path, unconditional form.

A direction is invalid if any clause is rejected, unknown if any clause did not complete, and valid otherwise.
Only programs Verus accepts are compared. Others are recorded with accepted false and no labels.
Run in the container from the release root. No model calls.

    python3.11 -I analysis/rq5_labels.py --items items.jsonl --out labels.jsonl --workers 10
items: {"label", "task", "generated"}
"""
from __future__ import annotations

import argparse
import csv
import json
from multiprocessing import Pool
from pathlib import Path
import sys

RELEASE = "/workspace"
DIRECTIONS = {
    "L1": dict(source_side="generated", clause_kind="requires", implication_direction="reference_implies_generated_clause"),
    "L2": dict(source_side="reference", clause_kind="ensures", implication_direction="generated_implies_reference_clause"),
    "L3": dict(source_side="reference", clause_kind="requires", implication_direction="generated_implies_reference_clause"),
    "L4": dict(source_side="generated", clause_kind="ensures", implication_direction="reference_implies_generated_clause"),
}


def label(item: dict) -> dict:
    sys.path.insert(0, RELEASE)
    import metrics_rebuild.share.lemma_implication as li
    import metrics_rebuild.share.llm_client as llm
    import metrics_rebuild.share.smt as smt
    from metrics_rebuild.share.functions import strength_contexts_for_path

    def blocked(*args, **kwargs):
        raise RuntimeError("LLM calls are disabled")

    llm.call_llm_json = blocked
    li.set_lemma_verus_binary("/opt/verus/verus")
    with Path(RELEASE, "data/evaluation/target_functions.csv").open() as stream:
        target = next(r for r in csv.DictReader(stream) if r["task_id"] == item["task"])
    generated, reference = item["generated"], target["reference_path"]
    from metrics_rebuild.share.verus_runner import verus_staged_verification_to_dict
    row = {**item, "accepted": verus_staged_verification_to_dict(generated).get("success") is True}
    if not row["accepted"]:
        return row
    for name, arguments in DIRECTIONS.items():
        li._LEMMA_CACHE.clear()
        try:
            result = smt.clause_implication_metric(strength_contexts_for_path(generated), strength_contexts_for_path(reference),
                                                   reference_rs_path=reference, metric_kind="x", note="x",
                                                   generated_rs_path=generated, **arguments)
        except Exception as error:
            row[name] = f"error: {type(error).__name__}"
            continue
        statuses = [(d.get("implication_check") or {}).get("status") for f in result["functions"]
                    if f["function"] == target["target_function"] for d in f["details"]]
        row[name] = "invalid" if "invalid" in statuses else ("valid" if statuses and all(s == "valid" for s in statuses) else "unknown")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    items = [json.loads(line) for line in args.items.read_text().splitlines() if line.strip()]
    with args.out.open("w") as stream, Pool(args.workers) as pool:
        for row in pool.imap_unordered(label, items):
            stream.write(json.dumps(row) + "\n")
            stream.flush()


if __name__ == "__main__":
    main()
