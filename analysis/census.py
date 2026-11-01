"""Census driver: turns rejected clause lemmas into one verdict table.

Only a positive Verus result is a verdict. The steps run in this order, stopping at the first verdict:

    items      rejected L1 and L2 clauses on accepted artifacts, for dev or census tasks
    gate2_regenerate.py   harnesses, and a check that context and status match the release
    jobs       job file for witness.py
    witness.py            counterexamples, no model
    gate2_tier0.py        proofs with no model
    open       what is still undecided, for tier_batch.py (Haiku, then Sonnet)
    verdicts   the final table, one row per clause

A witness counts for the form it verified on. An unconditional proof also proves the guarded form, and a
guarded refutation also refutes the unconditional form, so each pair needs at most two searches. Where
both forms are one formula they share a verdict. A lemma with both verdicts stops the run.

    python3 -I analysis/census.py items --release REL --dev-tasks results/tasks/dev_tasks.txt --split dev --out items.jsonl
    python3 -I analysis/census.py jobs --release REL --items items.jsonl --out jobs.jsonl
    python3 -I analysis/census.py open --regen regen.jsonl --harness DIR --witness out.jsonl --tier0 tier0.jsonl \\
        [--batch verdicts.jsonl ...] --out open.jsonl
    python3 -I analysis/census.py verdicts ... --out verdicts.jsonl

For RQ4, `rq4-items` runs in the container on rq4_generate.py's finals. It records each program's
verification stage and writes items for the accepted ones, and the steps above then run as usual.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Iterable

METRIC = {"L1": "precondition_clause_reliability_rate", "L2": "postcondition_clause_reliability_rate"}
COLUMN = {"L1": "pre_ref_to_gen", "L2": "post_gen_to_ref"}
SETTLED = ("proved", "refuted")


def rows_of(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def csv_rows(path: Path) -> list[dict]:
    with path.open() as stream:
        return list(csv.DictReader(stream))


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    rows = list(rows)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return len(rows)


def items(args: argparse.Namespace) -> None:
    dev = set(args.dev_tasks.read_text().split())
    root = args.release
    index = {r["sample_id"]: r["result_path"] for r in csv_rows(root / "data/evaluation/artifact_index.csv")}
    targets = {r["task_id"]: r["target_function"] for r in csv_rows(root / "data/evaluation/target_functions.csv")}
    out = []
    for row in csv_rows(root / "data/evaluation/rq1_artifact_outcomes.csv"):
        if row["verification_stage"] != "accepted" or (row["task_id"] in dev) != (args.split == "dev"):
            continue
        for direction in ("L1", "L2"):
            if row[COLUMN[direction]] != "invalid":
                continue
            record = json.loads((root / index[row["sample_id"]]).read_text())["metrics"][METRIC[direction]]["generated"]
            for function in record["functions"]:
                if function["function"] != targets[row["task_id"]]:
                    continue
                for detail in function["details"]:
                    check = detail.get("implication_check") or {}
                    if check.get("status") == "invalid":
                        name = check["obligation_context"]["check_name"]
                        out.append({"id": f"{row['sample_id'].replace('|', '__')}__{direction}__{name.rsplit('_', 1)[-1]}",
                                    "sample": row["sample_id"], "task": row["task_id"], "direction": direction, "check": name})
    out.sort(key=lambda item: item["id"])
    print(write_jsonl(args.out, out), "clauses,", len({i["sample"] for i in out}), "artifacts,", len({i["task"] for i in out}), "tasks")


def rq4_items(args: argparse.Namespace) -> None:
    import os
    sys.path.insert(0, str(args.release))
    os.chdir(args.release)
    from metrics_rebuild.share.verus_runner import verus_staged_verification_to_dict
    targets = {r["task_id"]: r["target_function"] for r in csv_rows(args.release / "data/evaluation/target_functions.csv")}
    stages, out = [], []
    for row in rows_of(args.finals):
        accepted = verus_staged_verification_to_dict(row["generated"]).get("success") is True
        stages.append({"task": row["task"], "accepted": accepted, "label": f"{args.label}|{row['task']}"})
        if accepted:
            for direction in ("L1", "L2"):
                out.append({"id": f"{args.label}__{row['task']}__{direction}", "label": f"{args.label}|{row['task']}", "direction": direction,
                            "task": row["task"], "generated": row["generated"], "function": targets[row["task"]]})
    write_jsonl(args.stages, stages)
    print(write_jsonl(args.out, out), "items,", sum(s["accepted"] for s in stages), "of", len(stages), "accepted")


def jobs(args: argparse.Namespace) -> None:
    root = args.release
    generated = {r["sample_id"]: r["generated_path"] for r in csv_rows(root / "data/generated/manifest.csv")}
    targets = {r["task_id"]: r for r in csv_rows(root / "data/evaluation/target_functions.csv")}
    grouped: dict[str, dict] = {}
    for item in rows_of(args.items):
        sample = item.get("sample") or item["label"]
        generated.setdefault(sample, item.get("generated"))
        grouped.setdefault(sample, {"task": item["task"], "directions": set()})["directions"].add(item["direction"])
    out = [{"sample": sample, "generated": generated[sample], "reference": targets[g["task"]]["reference_path"],
            "task_reference": targets[g["task"]]["reference_path"], "function": targets[g["task"]]["target_function"],
            "directions": sorted(g["directions"]), "forms": ["unconditional", "guarded"], "only_status": ["invalid"],
            "task": g["task"]} for sample, g in sorted(grouped.items())]
    print(write_jsonl(args.out, out), "jobs")


def same_formula(harness: Path, item_id: str) -> bool:
    def antecedent(form: str):
        path = harness / item_id / f"{form}.json"
        return json.loads(path.read_text())["antecedent"] if path.exists() else None
    guarded = antecedent("guarded")
    return guarded is None or guarded == antecedent("uncond")


def settle(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    """One row per clause, and the lemmas that got both verdicts."""
    verdicts: dict[tuple[str, str], list[dict]] = {}

    def add(item_id: str, form: str, verdict: str, tier: str, **extra) -> None:
        verdicts.setdefault((item_id, form), []).append({"verdict": verdict, "tier": tier, **extra})

    regen = rows_of(args.regen)
    ids = {}
    for row in regen:
        check = row["check"]
        row["sample"] = row.get("sample") or row["label"]
        form_keys = {"uncond": ("single" if row["direction"] == "L1" else "unconditional", check)}
        if row["direction"] == "L2":
            form_keys["guarded"] = ("guarded", f"guarded_{check}")
        for form, (name, wcheck) in form_keys.items():
            ids[(row["sample"], row["function"], row["direction"], name, wcheck)] = (row["id"], form)
    for record in rows_of(args.witness):
        where = ids.get((record.get("sample"), record.get("function"), record.get("direction"), record.get("form"), record.get("check")))
        if where and record.get("verdict") == "refuted":
            realization = record.get("realization") or {}
            add(*where, "refuted", f"witness:{record['tier']}", computed=bool(record.get("computed")),
                realized=realization.get("realized"), witness=record.get("witness"))
    for row in rows_of(args.tier0):
        if row["tier0"]:
            add(row["id"], row["form"], "proved", f"tier0:{row['by']}")
    for path in args.batch or []:
        for row in rows_of(path):
            if row.get("outcome") in SETTLED:
                add(row["id"], row["form"], row["outcome"], f"batch:{path.stem}")
    table, both = [], []
    for row in regen:
        one = row["direction"] == "L1" or same_formula(args.harness, row["id"])
        found = {form: list(verdicts.get((row["id"], form), [])) for form in ("uncond", "guarded")}
        if one:
            found["uncond"] += found["guarded"]
            found["guarded"] = list(found["uncond"])
        else:
            found["guarded"] += [{**f, "tier": "propagated"} for f in found["uncond"] if f["verdict"] == "proved"]
            found["uncond"] += [{**f, "tier": "propagated"} for f in found["guarded"] if f["verdict"] == "refuted"]
        entry = {k: row.get(k) for k in ("id", "sample", "task", "function", "direction", "check", "context_same")}
        entry["forms"] = 1 if one else 2
        for form in ("uncond", "guarded"):
            kinds = {f["verdict"] for f in found[form]}
            if len(kinds) > 1:
                both.append({"id": row["id"], "form": form, "found": found[form]})
            first = found[form][0] if found[form] else {"verdict": "undecided", "tier": None}
            plain = next((f for f in found[form] if not f.get("computed")), first)
            entry[form] = plain
        table.append(entry)
    return table, both


def open_lemmas(args: argparse.Namespace) -> None:
    table, both = settle(args)
    if both:
        sys.exit(f"{len(both)} lemmas have both verdicts: {both[:3]}")
    out = []
    for entry in table:
        for form in ("uncond",) if entry["forms"] == 1 else ("guarded", "uncond"):
            if entry[form]["verdict"] == "undecided":
                out.append({"id": entry["id"], "form": form})
    print(write_jsonl(args.out, out), "open lemmas")


def final(args: argparse.Namespace) -> None:
    table, both = settle(args)
    write_jsonl(args.out, table)
    print(len(table), "clauses,", len(both), "with both verdicts")
    if both:
        write_jsonl(args.out.with_suffix(".conflicts.jsonl"), both)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("items")
    one.add_argument("--release", type=Path, required=True)
    one.add_argument("--dev-tasks", type=Path, required=True)
    one.add_argument("--split", choices=("dev", "census"), required=True)
    one.add_argument("--out", type=Path, required=True)
    one.set_defaults(run=items)
    four = commands.add_parser("rq4-items")
    four.add_argument("--release", type=Path, required=True)
    four.add_argument("--finals", type=Path, required=True)
    four.add_argument("--label", default="haiku-5-5")
    four.add_argument("--stages", type=Path, required=True)
    four.add_argument("--out", type=Path, required=True)
    four.set_defaults(run=rq4_items)
    two = commands.add_parser("jobs")
    two.add_argument("--release", type=Path, required=True)
    two.add_argument("--items", type=Path, required=True)
    two.add_argument("--out", type=Path, required=True)
    two.set_defaults(run=jobs)
    for name, run in (("open", open_lemmas), ("verdicts", final)):
        command = commands.add_parser(name)
        command.add_argument("--regen", type=Path, required=True)
        command.add_argument("--harness", type=Path, required=True)
        command.add_argument("--witness", type=Path, required=True)
        command.add_argument("--tier0", type=Path, required=True)
        command.add_argument("--batch", type=Path, nargs="*")
        command.add_argument("--out", type=Path, required=True)
        command.set_defaults(run=run)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
