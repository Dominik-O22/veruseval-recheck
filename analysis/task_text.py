"""RQ5 inputs: public task text per task, and the seeded sample.

Text comes from MBPP (`text`), HumanEval (`prompt`) and `vc-description` in the public VeriCoding repository.
Only `VerusBench_MBPP_task_id_N` shares public MBPP numbering. `MBPP-verified_task_N` and `HumanEval-Verus_task_N`
do not, so those match on the target function's name, and a task with no single match gets no text.
VeriCoding's dafnybench entries are left out, because their descriptions are leftover code comments.
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


def task_text(sources: Path, targets: dict[str, str]) -> dict[str, str]:
    with (sources / "mbpp.jsonl").open() as stream:
        rows = list(map(json.loads, stream))
    mbpp = {r["task_id"]: r["text"] for r in rows}
    mbpp_names: dict[str, list[str]] = {}
    for row in rows:
        for name in re.findall(r"^def (\w+)\(", row["code"], re.M):
            mbpp_names.setdefault(name.lower(), []).append(row["text"])
    with gzip.open(sources / "HumanEval.jsonl.gz", "rt") as stream:
        humaneval = {r["entry_point"].lower(): r["prompt"] for r in map(json.loads, stream)}
    vericoding = {}
    for name in ("apps", "numpy_triple"):
        for line in (sources / f"verus_{name}.jsonl").read_text().splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                vericoding[row["id"]] = row.get("vc-description") or ""
    out = {}
    for task, function in targets.items():
        name = function.lower()
        m = re.fullmatch(r"VerusBench_MBPP_task_id_(\d+)", task)
        v = re.search(r"VeriCoding_(V[A-Z]\d+)_", task)
        if m:
            text = mbpp.get(int(m[1]))
        elif task.startswith("MBPP-verified"):
            matches = mbpp_names.get(name, [])
            text = matches[0] if len(matches) == 1 else None
        elif task.startswith("HumanEval-Verus"):
            text = humaneval.get(name)
        else:
            text = vericoding.get(v[1]) if v else None
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
        targets = {r["task_id"]: r["target_function"] for r in csv.DictReader(stream)}
    dev = set((repo / "results/tasks/dev_tasks.txt").read_text().split())
    hidden = set((repo / "results/tasks/hidden_constant_tasks.txt").read_text().split())
    text = task_text(args.sources, targets)
    args.out.write_text("".join(json.dumps({"task": t, "text": x}) + "\n" for t, x in sorted(text.items())))
    pool = [t for t in text if t not in dev]
    rng = random.Random(SEED)
    chosen = [t for t in pool if t in hidden]     # every hidden-constant task, for power
    pick = chosen + rng.sample([t for t in pool if t not in hidden], 200 - len(chosen))
    args.sample.write_text("\n".join(sorted(pick)) + "\n")
    args.sample.with_name("rq5_pool.txt").write_text("\n".join(sorted(pool)) + "\n")
    print(len(text), "tasks with text,", len(pool), "outside dev,", sum(t in hidden for t in pool), "hidden-constant among them")


if __name__ == "__main__":
    main()
