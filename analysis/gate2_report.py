"""Gate 2 report: re-check every claimed verdict with Verus and build the result tables.

Every proof and witness named in the agent logs is re-run through gate2_check.py here; a verdict
counts only if this re-run is positive. Guarded forms proved at tier 0 (empty body) come from
gate2_tier0.py. Propagation: a guarded refutation is an unconditional refutation (the same witness is
re-run on the unconditional harness), and an unconditional proof implies the guarded one.

    python3 -I analysis/gate2_report.py --work /work --repo .
Writes results/gate2/clauses.csv, results/gate2/summary.md and copies proof text and witnesses
(no reference code) to proofs/gate2/<id>/.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate2_check import prove, refute  # noqa: E402

WORK = None


def type_class(params: list[list[str]], harness: str) -> str:
    types = " ".join(t for _, t in params)
    if re.search(r"\bf(32|64)\b", types):
        return "float"
    if re.search(r"\b(int|nat|Seq|Map|Set)\b", types):
        return "spec int/collection"
    if re.search(r"\bchar\b|\bstr\b|String|\bu8\b.*Vec|Vec<u8>", types):
        return "char/string"
    if re.search(r"Vec<\s*Vec|\(Vec", types):
        return "nested collection"
    if re.search(r"Vec|\[", types):
        return "int/bool collection"
    if re.search(r"\b[A-Z]\w*\b", types.replace("Option", "")):
        return "struct/enum/generic"
    return "scalar"


def recheck(job):
    ident, form, kind, path = job
    harness = (Path(WORK) / "harness" / ident / f"{form}.rs").read_text()
    attempt = Path(path).read_text()
    if kind == "prove":
        rlimit = "100"  # gate2_check accepts --rlimit 100; the re-check always allows it
        result = prove(harness, attempt, rlimit)
        return job, result["outcome"] == "proved", result
    result = refute(harness, json.loads(attempt))
    return job, result["outcome"] == "refuted", result


def main() -> None:
    global WORK
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="/work")
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    WORK = args.work
    work = Path(args.work)
    regen = {}
    for line in (work / "regen.jsonl").read_text().splitlines():
        r = json.loads(line)
        regen[r["id"]] = r
    units = {u["id"]: u for u in json.loads((work / "units.json").read_text())}
    tier0 = {(r["id"], r["form"]): r for r in map(json.loads, (work / "tier0.jsonl").read_text().splitlines())}
    regrade = {json.loads(l)["id"] for l in (work / "items/regrade14.jsonl").read_text().splitlines()}
    dev100 = {json.loads(l)["id"] for l in (work / "items/dev100.jsonl").read_text().splitlines()}
    logs = []
    for path in sorted((work / "agent_logs").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                logs.append({**json.loads(line), "batch": path.stem})
    # Last log line per (id, form) wins (agents may append a corrected line).
    claims = {}
    for row in logs:
        claims[(row["id"], row["form"])] = row

    jobs = []
    for (ident, form), row in claims.items():
        if row.get("verdict") in ("proved", "refuted") and row.get("file"):
            kind = "prove" if row["verdict"] == "proved" else "refute"
            jobs.append((ident, form, kind, row["file"]))
            # propagation re-runs
            if kind == "refute" and form == "guarded" and units[ident]["direction"] == "L2":
                jobs.append((ident, "uncond", "refute", row["file"]))
    with Pool(args.workers) as pool:
        checked = {job[:3]: (ok, res) for job, ok, res in pool.imap_unordered(recheck, jobs)}

    out_rows = []
    problems = []
    for ident, unit in units.items():
        r = regen[ident]
        harness = (work / "harness" / ident / "uncond.rs").read_text()
        verdict = {"uncond": "undecided", "guarded": "undecided"}
        how = {"uncond": "", "guarded": ""}
        effort = {"uncond": {}, "guarded": {}}
        if unit["direction"] == "L2" and unit["guarded_tier0"]:
            verdict["guarded"], how["guarded"] = "proved", f"tier0:{tier0[(ident, 'guarded')]['by']}"
        for form in ("uncond", "guarded"):
            row = claims.get((ident, form))
            if not row:
                continue
            effort[form] = row
            covers = row.get("covers") or [form]
            if row.get("verdict") in ("proved", "refuted") and row.get("file"):
                kind = "prove" if row["verdict"] == "proved" else "refute"
                ok, res = checked.get((ident, form, kind), (False, {}))
                if not ok and row.get("propagated") == "uncond":
                    continue  # implied by the unconditional proof, handled below
                if not ok:
                    problems.append(f"{ident} {form}: claimed {row['verdict']} but re-check gave {res.get('outcome')}")
                    continue
                for f in covers:
                    if verdict[f] == "undecided":
                        verdict[f], how[f] = row["verdict"], f"agent:try{row.get('try')}"
                if kind == "refute" and form == "guarded" and unit["direction"] == "L2":
                    ok2, res2 = checked.get((ident, "uncond", "refute"), (False, {}))
                    if ok2 and verdict["uncond"] == "undecided":
                        verdict["uncond"], how["uncond"] = "refuted", "propagated:guarded witness"
                    elif not ok2:
                        problems.append(f"{ident}: guarded witness did not refute uncond ({res2.get('outcome')})")
                if kind == "prove" and form == "uncond" and verdict["guarded"] == "undecided" and unit["direction"] == "L2":
                    verdict["guarded"], how["guarded"] = "proved", "propagated:uncond proof"
        if unit["direction"] == "L1" or unit["same_formula"]:
            verdict["guarded"], how["guarded"] = verdict["uncond"], "same formula" if unit["direction"] == "L2" else "L1: one form"
        groups = [g for g, s in (("regrade14", regrade), ("dev100", dev100)) if ident in s]
        if ident.startswith("haiku"):
            groups = ["haiku7"]
        e_u, e_g = effort["uncond"], effort["guarded"]
        out_rows.append({
            "id": ident, "sample": r.get("sample") or f"haiku-5-5|{r.get('run')}|{r['task']}",
            "task": r["task"], "function": r["function"], "direction": unit["direction"], "check": r["check"],
            "groups": "+".join(groups), "type_class": type_class(unit["params"], harness),
            "recursive_spec": bool(re.search(r"spec fn \w+[^{;]*?decreases", harness, re.S)),
            "forms": "one" if unit["direction"] == "L1" or unit["same_formula"] else "two",
            "guarded": verdict["guarded"], "uncond": verdict["uncond"],
            "guarded_by": how["guarded"], "uncond_by": how["uncond"],
            "uncond_tool_calls": e_u.get("tool_calls"), "uncond_rough_tokens": e_u.get("rough_tokens"),
            "uncond_runs": (e_u.get("runs_prove") or 0) + (e_u.get("runs_refute") or 0) if e_u else None,
            "guarded_tool_calls": e_g.get("tool_calls"), "guarded_rough_tokens": e_g.get("rough_tokens"),
            "guarded_runs": (e_g.get("runs_prove") or 0) + (e_g.get("runs_refute") or 0) if e_g else None,
            "note": (e_g.get("note", "") + " | " if e_g else "") + (e_u.get("note", "") if e_u else ""),
        })
        # copy proof text / witnesses (never the harness)
        for form in ("uncond", "guarded"):
            row = claims.get((ident, form))
            if row and row.get("file") and verdict[form] in ("proved", "refuted"):
                src = Path(row["file"])
                text = src.read_text()
                if "spec fn" in text and row["verdict"] == "proved":
                    problems.append(f"{ident} {form}: proof text defines a spec fn; review before commit")
                dest = args.repo / "proofs/gate2" / ident
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest / f"{form}{''.join(src.suffixes)}")

    target = args.repo / "results/gate2"
    target.mkdir(parents=True, exist_ok=True)
    with (target / "clauses.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(sorted(out_rows, key=lambda x: x["id"]))
    (target / "problems.txt").write_text("\n".join(problems) + ("\n" if problems else ""))
    print(f"{len(out_rows)} clauses, {len(problems)} problems")
    for p in problems:
        print("  ", p)
    for group in ("regrade14", "haiku7", "dev100"):
        rows = [x for x in out_rows if group in x["groups"]]
        grid = Counter((x["guarded"], x["uncond"]) for x in rows)
        print(group, len(rows), dict(grid))


if __name__ == "__main__":
    main()
