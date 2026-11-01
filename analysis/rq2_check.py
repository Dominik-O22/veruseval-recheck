"""RQ2: does a sound, same-code contract show that the reference rejects an input the code handles?

Candidates are accepted artifacts on tasks outside the numeric list whose executable code matches the
input under the fixed lynette, with every L1 and L2 valid or proved and a rejected L3. The search runs
the frozen witness.py on L3, by pointing its L1 slot at L3 when this script starts, so the engine file
stays unchanged. A witness counts only if it is plain, verified with a clean control, and ran.

    host:       python3 -I analysis/rq2_check.py select --release REL --verdicts verdicts.jsonl \\\\
                    --numeric results/tasks/hidden_constant_tasks.txt --lynette BIN --tasks TASKS.txt --out jobs.jsonl
    container:  python3.11 -I analysis/rq2_check.py search --jobs jobs.jsonl --out witness.jsonl --workers 10
    host:       python3 -I analysis/rq2_check.py table --witness witness.jsonl --out rq2.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
from multiprocessing import Pool
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))


def csv_rows(path: Path) -> list[dict]:
    with path.open() as stream:
        return list(csv.DictReader(stream))


def select(args: argparse.Namespace) -> None:
    root = args.release
    numeric = set(args.numeric.read_text().split())
    allowed = set(args.tasks.read_text().split())
    generated = {r["sample_id"]: r["generated_path"] for r in csv_rows(root / "data/generated/manifest.csv")}
    targets = {r["task_id"]: r for r in csv_rows(root / "data/evaluation/target_functions.csv")}
    open_clauses = {r["sample"] for r in map(json.loads, args.verdicts.read_text().splitlines())
                    if r["uncond"]["verdict"] != "proved"}
    seen = {r["sample"] for r in map(json.loads, args.verdicts.read_text().splitlines())}
    jobs, counts = [], {"candidates": 0, "same_code": 0}
    for row in csv_rows(root / "data/evaluation/rq1_artifact_outcomes.csv"):
        task, sample = row["task_id"], row["sample_id"]
        if row["verification_stage"] != "accepted" or task in numeric or task not in allowed or row["pre_gen_to_ref"] != "invalid":
            continue
        sound = "invalid" not in (row["pre_ref_to_gen"], row["post_gen_to_ref"]) or (sample in seen and sample not in open_clauses)
        if not sound or "unavailable" in (row["pre_ref_to_gen"], row["post_gen_to_ref"]):
            continue
        counts["candidates"] += 1
        source = next((root / "data/generation/X_code").glob(f"*/{task}.rs"))
        same = subprocess.run([str(args.lynette), "compare", str(source), str(root / generated[sample])], capture_output=True, text=True)
        if same.returncode == 0:
            counts["same_code"] += 1
            jobs.append({"sample": sample, "generated": generated[sample], "reference": targets[task]["reference_path"],
                         "task_reference": targets[task]["reference_path"], "function": targets[task]["target_function"],
                         "directions": ["L1"], "forms": ["unconditional"], "only_status": ["invalid"], "task": task})
    args.out.write_text("".join(json.dumps(j) + "\n" for j in jobs))
    print(counts, "tasks", len({j["task"] for j in jobs}))


def search(args: argparse.Namespace) -> None:
    import witness
    witness.ROOT = Path("/workspace").resolve()
    # L3 has one form and L1's candidate order, so it runs in L1's slot. Records say L1 and mean L3.
    witness.DIRECTION_ARGS["L1"] = dict(source_side="reference", clause_kind="requires",
                                        implication_direction="generated_implies_reference_clause")
    jobs = [json.loads(line) for line in args.jobs.read_text().splitlines() if line.strip()]
    with args.out.open("w") as stream, Pool(args.workers, initializer=witness._init_worker, initargs=("/workspace",)) as pool:
        for records, _ in pool.imap_unordered(witness.run_job, [(job, {}, None, True) for job in jobs]):
            for record in records:
                stream.write(json.dumps(record, default=str) + "\n")


def table(args: argparse.Namespace) -> None:
    rows: dict[str, dict] = {}
    for line in args.witness.read_text().splitlines():
        record = json.loads(line)
        hit = record.get("verdict") == "refuted" and not record.get("computed")
        ran = (record.get("realization") or {}).get("realized") is True
        row = rows.setdefault(record["sample"], {"sample": record["sample"], "task": record.get("task"), "refuted": False, "realized": None})
        if hit:
            row.update(refuted=True, realized=row["realized"] or ran)
    args.out.write_text("".join(json.dumps(r) + "\n" for r in rows.values()))
    print(len(rows), "artifacts,", sum(r["refuted"] and bool(r["realized"]) for r in rows.values()), "counted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("select")
    for name in ("release", "verdicts", "numeric", "lynette", "tasks", "out"):
        one.add_argument(f"--{name}", type=Path, required=True)
    one.set_defaults(run=select)
    two = commands.add_parser("search")
    two.add_argument("--jobs", type=Path, required=True)
    two.add_argument("--out", type=Path, required=True)
    two.add_argument("--workers", type=int, default=10)
    two.set_defaults(run=search)
    three = commands.add_parser("table")
    three.add_argument("--witness", type=Path, required=True)
    three.add_argument("--out", type=Path, required=True)
    three.set_defaults(run=table)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
