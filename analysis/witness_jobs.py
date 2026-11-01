"""Rebuild the job files for analysis/witness.py from its results tables.

The cloud session did not push its job files. A job's id hashes its contents, so a rebuilt job that
matches the id in the table is the job that ran. Rows of one table give one job file.

    python3 -I analysis/witness_jobs.py --release RELEASE --table results/gate2/lemmas_census_dev.csv --out jobs.jsonl
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path


def job_id(job: dict) -> str:
    return hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()[:16]


def rebuild(row: dict, targets: dict, generated: dict, variants: dict) -> dict:
    reference = targets[row["task"]]["reference_path"]
    job = {"sample": row["sample"], "task_reference": reference, "function": row["function"], "task": row["task"],
           "directions": ast.literal_eval(row["directions"]), "forms": ast.literal_eval(row["forms"])}
    if row.get("operator"):
        variant = variants[row["sample"]]
        return {**job, "generated": variant["mutant_path"], "operator": row["operator"],
                "reference": f"data/evidence/contract_variants/bases/{variant['base_key']}.rs",
                "variant_direction": row["variant_direction"]}
    job = {**job, "generated": generated[row["sample"]]["generated_path"], "reference": reference}
    return {**job, "only_status": ast.literal_eval(row["only_status"])} if row.get("only_status") else job


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    csv.field_size_limit(10**8)

    def table(path: Path, key: str) -> dict:
        with path.open() as stream:
            return {r[key]: r for r in csv.DictReader(stream)}

    targets = table(args.release / "data/evaluation/target_functions.csv", "task_id")
    generated = table(args.release / "data/generated/manifest.csv", "sample_id")
    variants = table(args.release / "data/evidence/paper_results/RQ3/results/variants/retained_variants.csv", "mutant_id")
    with args.table.open() as stream:
        rows = {r["job_id"]: r for r in csv.DictReader(stream)}
    jobs = {wanted: rebuild(row, targets, generated, variants) for wanted, row in rows.items()}
    mismatched = [wanted for wanted, job in jobs.items() if job_id(job) != wanted]
    if mismatched:
        raise SystemExit(f"{len(mismatched)} of {len(jobs)} rebuilt jobs do not match their id")
    args.out.write_text("".join(json.dumps(job) + "\n" for job in jobs.values()))
    print(len(jobs), "jobs, all ids match")


if __name__ == "__main__":
    main()
