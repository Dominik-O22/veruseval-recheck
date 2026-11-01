"""Tables for RQ1, RQ3 and RQ4 from the verdict table and the release's labels. No model calls, no Verus.

A clause lands in one class, by its guarded and unconditional verdicts:

    Difference     refuted in the guarded form, or on L1, by a plain witness
    Premise only   proved guarded, refuted unconditionally by a plain witness
    Solver limit   proved in both forms
    Guarded only   proved guarded, undecided unconditionally
    Certified false, unlocated   refuted unconditionally by a plain witness, guarded undecided
    Computed       the only refutation uses a computed value, which is never a real difference
    Undecided      nothing established

An artifact is, in order: Trivial if the paper's check holds, Difference if any clause is, Sound if every
rejected clause is Solver limit or Premise only, otherwise Undecided. Artifacts with no rejected clause are
Clean. L3 and L4 are out of scope, so none of these means equivalent or correct.

    python3 -I analysis/census_report.py --verdicts verdicts.jsonl --labels rq1_artifact_labels.csv --out DIR
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import random

CLASSES = ("Difference", "Premise only", "Solver limit", "Guarded only", "Certified false, unlocated", "Computed", "Undecided")
ARTIFACTS = ("Trivial", "Clean", "Sound", "Difference", "Undecided")


def plain_refuted(entry: dict) -> bool:
    return entry["verdict"] == "refuted" and not entry.get("computed")


def clause_class(row: dict) -> str:
    uncond, guarded = row["uncond"], row["guarded"]
    if plain_refuted(guarded) or (row["direction"] == "L1" and plain_refuted(uncond)):
        return "Difference"
    if guarded["verdict"] == "proved":
        if uncond["verdict"] == "proved":
            return "Solver limit"
        if plain_refuted(uncond):
            return "Premise only"
        return "Computed" if uncond["verdict"] == "refuted" else "Guarded only"
    if plain_refuted(uncond):
        return "Certified false, unlocated"
    return "Computed" if "refuted" in (uncond["verdict"], guarded["verdict"]) else "Undecided"


def artifact_class(classes: list[str], trivial: bool) -> str:
    if trivial:
        return "Trivial"
    if not classes:
        return "Clean"
    if "Difference" in classes:
        return "Difference"
    return "Sound" if all(c in ("Solver limit", "Premise only") for c in classes) else "Undecided"


def config(sample: str) -> str:
    return "|".join(sample.split("|")[:3])


def rq1(table: list[dict]) -> dict:
    grid = Counter((r["guarded"]["verdict"], r["uncond"]["verdict"]) for r in table)
    impossible = grid[("refuted", "proved")]
    return {"clauses": len(table), "classes": {c: sum(clause_class(r) == c for r in table) for c in CLASSES},
            "by_direction": {d: dict(Counter(clause_class(r) for r in table if r["direction"] == d)) for d in ("L1", "L2")},
            "grid": {f"{g} / {u}": n for (g, u), n in sorted(grid.items())}, "impossible_cell": impossible,
            "by_tier": dict(Counter((r["uncond"].get("tier") or "none").split(":")[0] for r in table))}


def artifacts(table: list[dict], labels: list[dict]) -> dict[str, str]:
    by_sample: dict[str, list[str]] = defaultdict(list)
    for row in table:
        by_sample[row["sample"]].append(clause_class(row))
    return {r["sample_id"]: artifact_class(by_sample.get(r["sample_id"], []), r["triviality_state"] == "unfavorable")
            for r in labels}


def rq3(classes: dict[str, str], labels: list[dict], table: list[dict]) -> dict:
    rejected = {r["sample"] for r in table}
    passing = [r["sample_id"] for r in labels if r["io_state"] == "favorable"]
    among = [s for s in passing if s in rejected]
    return {"io_passing": len(passing), "io_passing_with_rejection": len(among),
            "outcome": dict(Counter(classes[s] for s in among)),
            "by_config": {c: dict(Counter(classes[r["sample_id"]] for r in labels if config(r["sample_id"]) == c))
                          for c in sorted({config(r["sample_id"]) for r in labels})}}


def paired_bootstrap(left: list[int], right: list[int], rounds: int = 2000, seed: int = 20261102) -> tuple[float, float]:
    """95% interval for the mean paired difference, resampling tasks."""
    rng = random.Random(seed)
    pairs = list(zip(left, right))
    means = sorted(sum(a - b for a, b in rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(rounds))
    return means[int(rounds * 0.025)], means[int(rounds * 0.975) - 1]


def rq4(attempts: dict[str, dict[str, str]]) -> dict:
    """attempts: model -> task -> Not verified, or an artifact class. Every model has every task."""
    tasks = sorted(next(iter(attempts.values())))
    sound = ("Clean", "Sound")
    out: dict = {}
    for model, outcome in attempts.items():
        n = len(tasks)
        count = Counter(outcome[t] for t in tasks)
        low = sum(count[c] for c in sound)
        out[model] = {"tasks": n, "verified": n - count["Not verified"], "sound_low": low,
                      "sound_high": low + count["Undecided"], "difference": count["Difference"],
                      "undecided": count["Undecided"], "trivial": count["Trivial"]}
    haiku = attempts["haiku-5-5"]
    for model, outcome in attempts.items():
        if model != "haiku-5-5":
            left = [int(haiku[t] in sound) for t in tasks]
            right = [int(outcome[t] in sound) for t in tasks]
            out[model]["haiku_minus_model_sound"] = paired_bootstrap(left, right)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    table = [json.loads(line) for line in args.verdicts.read_text().splitlines() if line.strip()]
    with args.labels.open() as stream:
        labels = [r for r in csv.DictReader(stream) if r["verification_stage"] == "accepted" and r["analysis_eligible"] == "True"]
    classes = artifacts(table, labels)
    report = {"rq1": rq1(table), "artifacts": dict(Counter(classes.values())), "rq3": rq3(classes, labels, table)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tables.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("rq1", "artifacts")}, indent=1))


if __name__ == "__main__":
    main()
