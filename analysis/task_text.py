"""RQ5 inputs: public task text per task, and the seeded sample.

Text comes from MBPP (`text`), HumanEval (`prompt`) and `vc-description` in the public VeriCoding repository.
It stays outside the repository, because the sources are downloaded and not ours to redistribute.

    python3 -I analysis/task_text.py --release REL --sources DIR --out text.jsonl --sample results/tasks/rq5_tasks.txt
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
import random
import re

SEED = 20261102


def task_text(sources: Path, tasks: list[str]) -> dict[str, str]:
    with (sources / "mbpp.jsonl").open() as stream:
        mbpp = {r["task_id"]: r["text"] for r in map(json.loads, stream)}
    with gzip.open(sources / "HumanEval.jsonl.gz", "rt") as stream:
        humaneval = {r["task_id"]: r["prompt"] for r in map(json.loads, stream)}
    vericoding = {}
    for name in ("apps", "numpy_triple", "dafnybench"):
        for line in (sources / f"verus_{name}.jsonl").read_text().splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                vericoding[row["id"]] = row.get("vc-description") or ""
    out = {}
    for task in tasks:
        m = re.search(r"MBPP[-_a-zA-Z]*?_(?:task_id_|task_)(\d+)", task)
        h = re.search(r"HumanEval-Verus_task_(\d+)", task)
        v = re.search(r"VeriCoding_(V[A-Z]\d+)_", task)
        text = (mbpp.get(int(m[1])) if m else None) or (humaneval.get(f"HumanEval/{h[1]}") if h else None) or (vericoding.get(v[1]) if v else None)
        if text and text.strip():
            out[task] = text.strip()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    with (args.release / "data/evaluation/target_functions.csv").open() as stream:
        tasks = sorted(r["task_id"] for r in csv.DictReader(stream))
    dev = set((repo / "results/tasks/dev_tasks.txt").read_text().split())
    hidden = set((repo / "results/tasks/hidden_constant_tasks.txt").read_text().split())
    text = task_text(args.sources, tasks)
    args.out.write_text("".join(json.dumps({"task": t, "text": x}) + "\n" for t, x in sorted(text.items())))
    pool = [t for t in text if t not in dev]
    rng = random.Random(SEED)
    pick = rng.sample([t for t in pool if t in hidden], 50) + rng.sample([t for t in pool if t not in hidden], 50)
    args.sample.write_text("\n".join(sorted(pick)) + "\n")
    print(len(text), "tasks with text,", len(pool), "outside dev,", sum(t in hidden for t in pool), "hidden-constant among them")


if __name__ == "__main__":
    main()
