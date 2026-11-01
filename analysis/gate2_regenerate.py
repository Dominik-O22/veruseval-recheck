"""Gate 2, step 1: regenerate rejected per-clause L1/L2 lemmas in both comparison forms.

For each item (sample, direction, check name) this re-runs the release's per-clause path
(metrics_rebuild.share.smt.clause_implication_metric, as analysis/gate1_regenerate.py does) and
captures the exact harness Verus checked. Two forms:

  uncond   the release's own lemma, unchanged (the paper's form)
  guarded  the same per-clause call with the reference and generated `requires` prepended to
           the antecedent (L2 only; L1 already has the reference precondition as its antecedent,
           so for L1 the two forms are one formula)

The unconditional context and status must match the released record before a lemma is used.
Harnesses embed the release's reference files, so they are written outside this repository.
No model calls; llm_client is disabled.

    python3 -I analysis/gate2_regenerate.py --release /work/release --items items.jsonl --out /work/harness
items.jsonl rows: {"id", "sample", "direction", "task", "check"} or, for programs with no released
record, {"id", "generated", "direction", "task", "function"} (every rejected clause is emitted).
"""
from __future__ import annotations

import argparse
import contextvars
import csv
import json
from multiprocessing import Pool
from pathlib import Path
import sys

ARGS = None
DIRECTIONS = {
    "L1": ("pre_ref_to_gen", "precondition_clause_reliability_rate",
           dict(source_side="generated", clause_kind="requires",
                implication_direction="reference_implies_generated_clause")),
    "L2": ("post_gen_to_ref", "postcondition_clause_reliability_rate",
           dict(source_side="reference", clause_kind="ensures",
                implication_direction="generated_implies_reference_clause")),
}
CONTEXT = ("function", "check_name", "antecedent", "consequent", "antecedent_kinds", "consequent_kinds")
FORM = contextvars.ContextVar("form", default="uncond")


_SETUP = None


def setup(release: str):
    global _SETUP
    if _SETUP is not None:
        return _SETUP
    sys.path.insert(0, release)
    import os
    os.chdir(release)
    import metrics_rebuild.share.llm_client as llm
    def blocked(*a, **k):
        raise RuntimeError("LLM calls are disabled in gate 2")
    llm.call_llm_json = blocked
    import metrics_rebuild.share.lemma_implication as li
    import metrics_rebuild.share.smt as smt
    from metrics_rebuild.share._shared import materialize_contract_clauses
    li.set_lemma_verus_binary("/opt/verus/verus")
    captured: dict = {}
    original_run = li.subprocess.run
    original_check = smt.lemma_implication_check

    def run(command, *a, **k):
        result = original_run(command, *a, **k)
        if "--verify-function" in command:
            target = Path(command[-1])
            captured.setdefault("harness", {})[captured["key"]] = {
                "harness": target.read_text(), "lemma": command[command.index("--verify-function") + 1],
                "command": [str(c) for c in command[:-1]], "returncode": result.returncode}
        return result

    def check(**kw):
        form = FORM.get()
        captured["key"] = (kw["function_name"], kw["check_name"], form)
        if form == "guarded":
            ref = materialize_contract_clauses(kw["reference_context"].get("requires") or [], kind="requires",
                                               inject_implicit_true=False)
            gen = materialize_contract_clauses(kw["generated_context"].get("requires") or [], kind="requires",
                                               inject_implicit_true=False)
            kw["antecedent"] = ([{**c, "_lemma_source": "reference"} for c in ref]
                                + [{**c, "_lemma_source": "generated"} for c in gen] + list(kw["antecedent"]))
        return original_check(**kw)

    li.subprocess.run = run
    smt.lemma_implication_check = check
    _SETUP = (smt, captured)
    return _SETUP


def regenerate(item: dict) -> list[dict]:
    smt, captured = setup(ARGS.release)
    from metrics_rebuild.share.functions import strength_contexts_for_path
    root = Path(ARGS.release)
    _, metric, arguments = DIRECTIONS[item["direction"]]
    with (root / "data/evaluation/target_functions.csv").open() as stream:
        target = next(r for r in csv.DictReader(stream) if r["task_id"] == item["task"])
    reference = target["reference_path"]
    released = None
    if "sample" in item:
        with (root / "data/evaluation/artifact_index.csv").open() as stream:
            result_path = next(r["result_path"] for r in csv.DictReader(stream) if r["sample_id"] == item["sample"])
        record = json.loads((root / result_path).read_text())["metrics"][metric]["generated"]
        released = next(f for f in record["functions"] if f["function"] == target["target_function"])
        generated = released["details"][0]["implication_check"]["obligation_context"]["generated_path"]
        function = target["target_function"]
    else:
        generated, function = item["generated"], item["function"]
    rows = []
    forms = ("uncond", "guarded") if item["direction"] == "L2" else ("uncond",)
    out = {}
    for form in forms:
        FORM.set(form)
        captured.clear()
        # The release caches lemma results per process; pool workers are reused, so clear it to
        # make every item and form run Verus and leave its own harness.
        import metrics_rebuild.share.lemma_implication as li
        li._LEMMA_CACHE.clear()
        result = smt.clause_implication_metric(
            strength_contexts_for_path(generated), strength_contexts_for_path(reference),
            reference_rs_path=reference, metric_kind="x", note="x", generated_rs_path=generated, **arguments)
        out[form] = ({d["implication_check"]["obligation_context"]["check_name"]: d["implication_check"]
                      for f in result["functions"] if f["function"] == function for d in f["details"]
                      if d.get("implication_check")}, dict(captured.get("harness", {})))
    checks = [item["check"]] if "check" in item else [
        name for name, c in out["uncond"][0].items() if c.get("status") != "valid"]
    for name in checks:
        row = {**item, "check": name, "function": function}
        if "check" not in item:  # programs with no released record: one id per clause
            row["id"] = f"{item['id']}__{name.rsplit('_', 1)[-1]}"
        if released is not None:
            rel = next(d["implication_check"] for d in released["details"]
                       if d["implication_check"]["obligation_context"]["check_name"] == name)
            mine = out["uncond"][0].get(name)
            row["released"] = rel["status"]
            row["context_same"] = bool(mine) and all(
                rel["obligation_context"][k] == mine["obligation_context"][k] for k in CONTEXT)
        for form in forms:
            check, harnesses = out[form]
            c = check.get(name) or {}
            row[f"{form}_status"] = c.get("status")
            row[f"{form}_reason"] = c.get("reason")
            h = harnesses.get((function, name, form))
            if h:
                directory = Path(ARGS.out) / row["id"]
                directory.mkdir(parents=True, exist_ok=True)
                (directory / f"{form}.rs").write_text(h["harness"])
                (directory / f"{form}.json").write_text(json.dumps(
                    {"lemma": h["lemma"], "command": h["command"], "status": c.get("status"),
                     "antecedent": c.get("obligation_context", {}).get("antecedent"),
                     "consequent": c.get("obligation_context", {}).get("consequent")}, indent=1))
            row[f"{form}_harness"] = bool(h)
        rows.append(row)
    return rows


def main() -> None:
    global ARGS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    ARGS = parser.parse_args()
    ARGS.out = str(Path(ARGS.out).resolve())
    items = [json.loads(line) for line in ARGS.items.read_text().splitlines() if line.strip()]
    with ARGS.results.open("w") as stream, Pool(ARGS.workers) as pool:
        for rows in pool.imap_unordered(regenerate, items):
            for row in rows:
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
