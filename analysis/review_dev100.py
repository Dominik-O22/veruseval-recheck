"""Blind review on the gate 2 dev100 sample, scored against certified verdicts.

Runs the same prompt as review_specs.py on each distinct artifact behind the 100 clauses. The
review sees only the generated program: no reference, no flags, no verdicts.

Scoring is fixed before the run. Unit: one artifact in one direction, because a review reports on
a whole contract and each sampled clause covers one direction.
  L2: truth is a real difference if any sampled clause has guarded refuted, clear if every sampled
      clause has guarded proved. The review alarms if weak_post is non-empty.
  L1: truth is a real difference if any sampled clause is refuted, clear if every one is proved.
      The review alarms if extra_pre is non-empty.
  Anything else is undecided and is left out of the score.
Limit: only sampled clauses have a verdict, so an alarm on a clear unit may concern another clause.
That makes the false-alarm rate an upper bound.

Run inside the container from the release root, with ANTHROPIC_API_KEY set:
    python haiku/review_dev100.py run /repo/results/gate2/clauses.csv runs/review-dev100.jsonl
    python haiku/review_dev100.py score /repo/results/gate2/clauses.csv runs/review-dev100.jsonl
"""
from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_specs import ask


def samples(clauses: Path) -> list[dict]:
    with clauses.open() as stream:
        return [r for r in csv.DictReader(stream) if "dev100" in r["groups"]]


def generated_path(sample: str, direction: str) -> str:
    with (ROOT / "data/evaluation/artifact_index.csv").open() as stream:
        result = next(r["result_path"] for r in csv.DictReader(stream) if r["sample_id"] == sample)
    metric = "postcondition_clause_reliability_rate" if direction == "L2" else "precondition_clause_reliability_rate"
    record = json.loads((ROOT / result).read_text())["metrics"][metric]["generated"]
    for function in record["functions"]:
        for detail in function.get("details") or []:
            context = (detail.get("implication_check") or {}).get("obligation_context")
            if context:
                return context["generated_path"]
    raise LookupError(sample)


def review(item: tuple[str, str]) -> dict:
    sample, direction = item
    reply, cost = asyncio.run(ask((ROOT / generated_path(sample, direction)).read_text()))
    found = re.search(r"\{.*\}", reply, re.S)
    try:
        parsed = json.loads(found.group(0)) if found else {"raw": reply[:500]}
    except json.JSONDecodeError:
        parsed = {"raw": reply[:500]}
    return {"sample": sample, **parsed, "cost": cost}


def run(clauses: Path, out: Path) -> None:
    items = sorted({r["sample"]: r["direction"] for r in samples(clauses)}.items())
    with out.open("w") as stream, ThreadPoolExecutor(5) as pool:
        for result in pool.map(review, items):
            stream.write(json.dumps(result) + "\n")
            stream.flush()
    print(f"reviewed {len(items)} artifacts")


def score(clauses: Path, out: Path) -> None:
    reviews = {r["sample"]: r for r in map(json.loads, out.open())}
    units: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in samples(clauses):
        units[(row["sample"], row["direction"])].append(row["guarded"] if row["direction"] == "L2" else row["uncond"])
    table: Counter = Counter()
    for (sample, direction), verdicts in units.items():
        result = reviews[sample]
        if "raw" in result:
            table[("unparsed", direction)] += 1
            continue
        alarm = bool(result.get("weak_post" if direction == "L2" else "extra_pre"))
        truth = "difference" if "refuted" in verdicts else "clear" if set(verdicts) == {"proved"} else "undecided"
        table[(truth, direction, alarm)] += 1
    for key, n in sorted(table.items(), key=str):
        print(key, n)
    for direction in ("L1", "L2", None):
        total = lambda truth, alarm: sum(n for k, n in table.items() if len(k) == 3 and k[0] == truth
                                         and (direction is None or k[1] == direction) and k[2] is alarm)
        print(direction or "both", f"caught {total('difference', True)} of {total('difference', True) + total('difference', False)} real differences,",
              f"alarms on {total('clear', True)} of {total('clear', True) + total('clear', False)} clear units")
    print("cost", round(sum(r["cost"] for r in reviews.values()), 3), "artifacts", len(reviews))


if __name__ == "__main__":
    (run if sys.argv[1] == "run" else score)(Path(sys.argv[2]), Path(sys.argv[3]))
