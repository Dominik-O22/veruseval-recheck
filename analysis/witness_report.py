"""Tables for gate 2 from witness.py run records. No model calls, no Verus.

    python3 analysis/gate2_report.py --variants-dev runs/dev.jsonl --variants-holdout runs/holdout.jsonl \
        --fixtures runs/fixtures.jsonl --census-dev runs/census_dev.jsonl --control runs/control73_*.jsonl \
        --out results/gate2

Variant rule (plan, Validation 1): stronger preconditions (pre_strengthening) must be refuted on L1,
weaker postconditions (post_weakening) must be refuted on L2, and every other lemma of every variant
must not be refuted. A variant counts as refuted when any of its clause lemmas in that direction and
form has a verdict. A refutation where none is expected is reported, never dropped. Each one is then
read by hand and classified, because a verified witness on a lemma that is actually false is a correct
result for the engine and a wrong expectation, while a witness on a true lemma is a soundness bug.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import statistics

MUST = {"pre_strengthening": "L1", "post_weakening": "L2"}
OPERATORS = ["PRE_ADD", "PRE_REFINE", "PRE_REMOVE", "PRE_RELAX", "POST_ADD", "POST_REFINE", "POST_REMOVE", "POST_RELAX"]
DROP = ("screens", "rejected_hits", "confirmation", "generated", "reference", "task_reference")


def load(paths) -> list[dict]:
    out = []
    for path in paths or []:
        out += [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    return out


def variant_table(records: list[dict], split: str) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    for r in records:
        groups[(r["sample"], r.get("form"))].append(r)
    rows, unexpected = [], []
    for (sample, form), group in sorted(groups.items()):
        first = group[0]
        direction = first["direction"]
        expected = "refute" if MUST.get(first.get("variant_direction")) == direction else "clear"
        refuted = [r for r in group if r.get("verdict") == "refuted"]
        lemmas = [r for r in group if r.get("outcome") not in ("no_lemmas",)]
        row = {"split": split, "sample": sample, "task": first.get("task"), "operator": first.get("operator"),
               "variant_direction": first.get("variant_direction"), "direction": direction, "form": form,
               "expected": expected, "lemmas": len(lemmas), "refuted_lemmas": len(refuted),
               "result": ("refuted" if refuted else "missed") if expected == "refute"
               else ("UNEXPECTED_REFUTATION" if refuted else "cleared"),
               "release_rejected_lemmas": sum(r.get("release_status") == "invalid" for r in group),
               "errors": sum(r.get("outcome") in ("engine_error", "capture_error") for r in group),
               "no_harness": sum(r.get("outcome") == "no_harness" for r in group),
               "witness": json.dumps(refuted[0].get("witness")) if refuted else "",
               "refuted_checks": ";".join(r["check"] for r in refuted)}
        rows.append(row)
        if expected == "clear" and refuted:
            for r in refuted:
                unexpected.append({"split": split, "key": r["key"], "operator": first.get("operator"),
                                   "release_status": r.get("release_status"), "witness": json.dumps(r.get("witness"))})
    return rows, unexpected


def recall_by_operator(rows: list[dict]) -> list[dict]:
    out = []
    for split in sorted({r["split"] for r in rows}):
        for form_group in (("single",), ("unconditional",), ("guarded",)):
            for op in OPERATORS:
                sub = [r for r in rows if r["split"] == split and r["operator"] == op and r["form"] in form_group]
                if not sub:
                    continue
                must = [r for r in sub if r["expected"] == "refute"]
                clear = [r for r in sub if r["expected"] == "clear"]
                out.append({"split": split, "form": form_group[0], "operator": op,
                            "must_refute": len(must), "refuted": sum(r["result"] == "refuted" for r in must),
                            "missed": sum(r["result"] == "missed" for r in must),
                            "recall": round(sum(r["result"] == "refuted" for r in must) / len(must), 4) if must else "",
                            "must_clear": len(clear), "cleared": sum(r["result"] == "cleared" for r in clear),
                            "unexpected_refutations": sum(r["result"] == "UNEXPECTED_REFUTATION" for r in clear)})
    return out


def gate_summary(rows: list[dict]) -> list[dict]:
    """The gate's own unit: one must-refute variant, in its own direction, form as the paper uses it."""
    out = []
    for split in sorted({r["split"] for r in rows}):
        for label, forms in (("paper form (L1, unconditional L2)", ("single", "unconditional")),
                             ("guarded L2 in place of unconditional", ("single", "guarded"))):
            sub = [r for r in rows if r["split"] == split and r["form"] in forms]
            must = [r for r in sub if r["expected"] == "refute"]
            clear = [r for r in sub if r["expected"] == "clear"]
            hit = sum(r["result"] == "refuted" for r in must)
            out.append({"split": split, "forms": label, "must_refute": len(must), "refuted": hit,
                        "recall": round(hit / len(must), 4) if must else "",
                        "must_clear_rows": len(clear),
                        "unexpected_refutations": sum(r["result"] == "UNEXPECTED_REFUTATION" for r in clear)})
    return out


def type_class_table(records: list[dict], source: str) -> list[dict]:
    counts = defaultdict(Counter)
    for r in records:
        if r.get("outcome") in ("not_searched", "no_lemmas", None):
            continue
        classes = r.get("type_classes") or (["unsupported"] if r.get("outcome") == "unsupported_type" else ["(no harness)"])
        realization = (r.get("realization") or {})
        for c in classes:
            k = counts[c]
            k["lemmas"] += 1
            k["searched"] += r.get("outcome") in ("refuted", "undecided")
            k["refuted"] += r.get("verdict") == "refuted"
            k["unsupported_type"] += r.get("outcome") == "unsupported_type"
            k["no_harness"] += r.get("outcome") == "no_harness"
            k["engine_error"] += r.get("outcome") in ("engine_error", "capture_error")
            k["all_screens_failed_to_compile"] += bool(r.get("screens")) and all(
                s.get("frontend_failed") or s.get("bound") == 0 for s in r["screens"])
            k["void_controls"] += sum(h.get("failure") == "void_control_verified" for h in r.get("rejected_hits") or [])
            k["inconclusive_controls"] += sum(h.get("failure") == "control_inconclusive" for h in r.get("rejected_hits") or [])
            if r.get("verdict") == "refuted":
                k["realized"] += realization.get("realized") is True
                k["unrepresentable"] += realization.get("realized") is False
                k["realization_not_run"] += realization.get("realized") is None
            if r.get("release_status") == "invalid":
                k["release_rejected"] += 1
                k["release_rejected_refuted"] += r.get("verdict") == "refuted"
    return [{"source": source, "type_class": c, **dict(k)} for c, k in sorted(counts.items())]


def timing(records: list[dict], source: str) -> list[dict]:
    out = []
    for outcome in ("refuted", "undecided"):
        secs = [r["seconds"] for r in records if r.get("outcome") == outcome and "seconds" in r]
        if secs:
            q = statistics.quantiles(secs, n=10) if len(secs) > 1 else [secs[0]] * 9
            out.append({"source": source, "outcome": outcome, "checks": len(secs),
                        "mean_s": round(statistics.mean(secs), 3), "median_s": round(statistics.median(secs), 3),
                        "p90_s": round(q[8], 3), "max_s": round(max(secs), 3), "total_s": round(sum(secs), 1)})
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def markdown(path: Path) -> str:
    rows = list(csv.DictReader(path.open())) if path.exists() and path.read_text().strip() else []
    if not rows:
        return "(none)\n"
    keys = list(rows[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(r.get(k) or "") for k in keys) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def slim(records: list[dict]) -> list[dict]:
    keep = []
    for r in records:
        row = {k: v for k, v in r.items() if k not in DROP}
        conf = r.get("confirmation") or {}
        row["control_clean_failure"] = conf.get("control_clean_failure")
        row["realized"] = (r.get("realization") or {}).get("realized")
        row["realization_reason"] = (r.get("realization") or {}).get("reason")
        row["screen_batches"] = len(r.get("screens") or [])
        row["screen_compile_failures"] = sum(bool(s.get("frontend_failed")) for s in r.get("screens") or [])
        row["rejected_hits"] = ";".join(h.get("failure", "") for h in r.get("rejected_hits") or [])
        keep.append(row)
    return keep


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants-dev", nargs="*")
    parser.add_argument("--variants-holdout", nargs="*")
    parser.add_argument("--fixtures", nargs="*")
    parser.add_argument("--census-dev", nargs="*")
    parser.add_argument("--control", nargs="*")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    variant_rows, unexpected = [], []
    sources = {"variants_dev": load(args.variants_dev), "variants_holdout": load(args.variants_holdout),
               "fixtures": load(args.fixtures), "census_dev": load(args.census_dev), "control": load(args.control)}
    for split, key in (("dev", "variants_dev"), ("holdout", "variants_holdout")):
        rows, bad = variant_table(sources[key], split)
        variant_rows += rows
        unexpected += bad
    write(args.out / "variant_rows.csv", variant_rows)
    write(args.out / "variant_recall_by_operator.csv", recall_by_operator(variant_rows))
    write(args.out / "variant_gate.csv", gate_summary(variant_rows))
    write(args.out / "variant_unexpected_refutations.csv", unexpected)
    classes, times = [], []
    for source, records in sources.items():
        if records:
            classes += type_class_table(records, source)
            times += timing(records, source)
            write(args.out / f"lemmas_{source}.csv", slim(records))
    write(args.out / "type_classes.csv", classes)
    both = [{"source": source, "key": r["key"], "witness": json.dumps(r.get("witness"))}
            for source, records in sources.items() for r in records
            if r.get("release_status") == "valid" and r.get("verdict") == "refuted"]
    write(args.out / "both_verdicts.csv", both)
    checked = sum(r.get("release_status") == "valid" and r.get("outcome") in ("refuted", "undecided")
                  for records in sources.values() for r in records)
    print(f"== both verdicts (Verus-proved lemma also refuted): {len(both)} of {checked} proved lemmas searched")
    write(args.out / "timing.csv", times)
    with (args.out / "tables.md").open("w") as md:
        for name in ("variant_gate.csv", "variant_recall_by_operator.csv", "variant_unexpected_refutations.csv",
                     "both_verdicts.csv", "type_classes.csv", "timing.csv"):
            md.write(f"### {name}\n\n{markdown(args.out / name)}\n")
    for name in ("variant_gate.csv", "variant_recall_by_operator.csv", "variant_unexpected_refutations.csv"):
        print(f"== {name}")
        print((args.out / name).read_text())


if __name__ == "__main__":
    main()
