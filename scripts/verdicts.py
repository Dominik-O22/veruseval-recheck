"""Combine evaluator labels with adjudicate.py verdicts into one verdict per task.

A contract counts as correct when every reliability direction (reference
precondition => generated, generated postcondition => reference) is valid or
was proved by the adjudicator, it is not trivial, and it accepts every correct
I/O case and rejects every wrong one. Remaining differences are then only in
the safe direction: a more permissive precondition or a stronger postcondition.

    python haiku/verdicts.py runs/haiku-fair20 [--label haiku-5-5]

A direction counts as resolved when every function's check in it was proved
or passed on a fresh recheck.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.rebuild_rq1_inputs import extract

RELIABILITY = ("pre_ref_to_gen", "post_gen_to_ref")
COMPLETENESS = ("pre_gen_to_ref", "post_ref_to_gen")


def verdict(label: dict, outcome: dict, proved: set[str]) -> tuple[str, list[str]]:
    if label["verification_stage"] != "accepted":
        return "not verified", [label["verification_stage"]]
    if all(label[k] == "favorable" for k in ("triviality_state", "io_state", "formal_state")):
        return "clean", []
    misses = []
    if label["triviality_state"] == "unfavorable":
        misses.append("trivial")
    misses += [f"{d} {outcome[d]}" for d in RELIABILITY if outcome[d] != "valid" and d not in proved]
    misses += [f"{k} failed {outcome[k + '_failed']}" for k in ("io_correct", "io_wrong") if outcome[k + "_failed"]]
    if misses:
        return "candidate real miss", misses
    safe = [f"{d} {outcome[d]}" for d in COMPLETENESS if outcome[d] != "valid" and d not in proved]
    safe += [f"io_invalid failed {outcome['io_invalid_failed']}"] if outcome["io_invalid_failed"] else []
    return "correct, differs only in safe direction", safe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--label", help="Only samples with this model label (default: all).")
    args = parser.parse_args()
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        catalog = {r["task_id"]: r for r in csv.DictReader(stream)}
    adjudication = json.loads((args.run / "adjudication.json").read_text()) \
        if (args.run / "adjudication.json").exists() else []
    tried: dict[tuple[str, str], list[str]] = {}
    for a in adjudication:
        tried.setdefault((a["sample"], a["direction"]), []).append(a["verdict"])
    tally = Counter()
    for path in sorted((args.run / "eval").rglob("per_file/*.json")):
        payload = json.loads(path.read_text())
        sample = payload["target_evaluation"]["sample_id"]
        if (args.label and f"|{args.label}|" not in sample) or not payload["target_evaluation"]["analysis_eligible"]:
            continue
        label, outcome = extract(payload, path, catalog[sample.split("|")[-1]])
        proved = {d for (s, d), v in tried.items()
                  if s == sample and all(x in ("proved", "valid_on_recheck") for x in v)}
        name, notes = verdict(label, outcome, proved)
        tally[name] += 1
        print(f"{sample:<72}{name:<42}{'; '.join(notes)}")
    print()
    for name, count in tally.most_common():
        print(f"{count:>3}  {name}")


if __name__ == "__main__":
    main()
