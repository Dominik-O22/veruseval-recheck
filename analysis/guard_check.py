"""Are guarded proofs meaningful? Looks for a real input that satisfies a guarded lemma's antecedent.

A guarded proof says nothing if no value satisfies both preconditions and the generated
postcondition. For each guarded-proved clause, this searches small literals for one that does, with
Verus as the judge. No model calls. Finding none is not evidence of vacuity. It stays unconfirmed.

    python3 -I analysis/guard_check.py --harness DIR --clauses clauses.csv --out guard.jsonl
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate2_check import SPEC_ONLY, lemma_signature
from tier_free import VERUS, candidates


def search(path: Path, limit: int) -> dict:
    harness = path.read_text()
    _, params, antecedent, _, _, _ = lemma_signature(harness)
    picks = candidates(params, limit)
    if picks is None:
        return {"status": "unsupported type", "tried": 0}
    parts = []
    for i, pick in enumerate(picks):
        lets = [f"    let {'ghost ' if SPEC_ONLY.match(t) else ''}{n}: {t} = {pick[n]};" for n, t in params]
        goals = [f"        assert({c});" for c in antecedent]
        parts.append(f"#[allow(unused_variables)]\nfn __sat_{i}() {{\n" + "\n".join(lets) + "\n    proof {\n" + "\n".join(goals) + "\n    }\n}\n")
    text = harness + "\nverus! {\n" + "\n".join(parts) + "} // guard check\n"
    with tempfile.TemporaryDirectory(prefix="sat_") as directory:
        file = Path(directory) / "sat.rs"
        file.write_text(text)
        try:
            run = subprocess.run([VERUS, "--crate-type=lib", "--verify-root", "--verify-function", "__sat_*", str(file)],
                                 capture_output=True, text=True, timeout=280)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "tried": len(picks)}
    log = run.stdout + run.stderr
    if "verification results" not in log:
        return {"status": "did not compile", "tried": len(picks)}
    lines = text.splitlines()
    starts = [(i + 1, int(re.match(r"fn __sat_(\d+)", l).group(1))) for i, l in enumerate(lines) if re.match(r"fn __sat_\d+", l)]
    failed = set()
    for number in re.findall(r"sat\.rs:(\d+):", log):
        owner = [n for line, n in starts if line <= int(number)]
        if owner:
            failed.add(owner[-1])
    passing = [i for i in range(len(picks)) if i not in failed]
    return {"status": "satisfiable" if passing else "no input found", "tried": len(picks),
            "input": picks[passing[0]] if passing else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--clauses", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()
    with args.clauses.open() as stream:
        rows = [r for r in csv.DictReader(stream) if r["direction"] == "L2" and r["forms"] == "two" and r["guarded"] == "proved"]
    with args.out.open("w") as stream, ThreadPoolExecutor(7) as pool:
        for row, result in zip(rows, pool.map(lambda r: search(args.harness / r["id"] / "guarded.rs", args.limit), rows)):
            stream.write(json.dumps({"id": row["id"], "uncond": row["uncond"], **result}) + "\n")
            stream.flush()


if __name__ == "__main__":
    main()
