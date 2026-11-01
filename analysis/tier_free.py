"""Free tier: search small concrete values for a counterexample to a regenerated lemma.

No model calls. For each harness it builds up to --limit candidate inputs and outputs, puts each in
its own witness function, and verifies them in one Verus run. Any candidate that passes is
re-checked one at a time by gate2_check.refute, which is the verdict of record.

    python3 -I analysis/tier_free.py --harness DIR --clauses clauses.csv --out free.jsonl
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import itertools
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate2_check import SPEC_ONLY, lemma_signature, refute

VERUS = "/opt/verus/verus"
SEED = 20261103
INTS = {"i8": 127, "i16": 32767, "i32": 2147483647, "i64": 9223372036854775807, "isize": 2147483647,
        "u8": 255, "u16": 65535, "u32": 4294967295, "u64": 18446744073709551615, "usize": 4294967295}


def values(kind: str, depth: int = 0) -> list[str] | None:
    """Small literals of a type, simplest first, or None if the type is not supported."""
    kind = kind.strip()
    if kind.startswith("&") and not kind.startswith("&["):
        inner = values(kind[1:], depth)
        return inner and [f"&{v}" for v in inner]
    if kind in INTS:
        signed = kind[0] == "i"
        picks = [0, 1, 2, 3, 5, 10, 100, INTS[kind]] + ([-1, -2, -INTS[kind] - 1] if signed else [])
        return [f"{v}{kind}" for v in picks]
    if kind == "bool":
        return ["true", "false"]
    if kind == "char":
        return ["'a'", "'0'", "' '"]
    if kind in ("f32", "f64"):
        return [f"{v}{kind}" for v in ("0.0", "1.0", "-1.0", "2.0")]
    match = re.fullmatch(r"Vec<(.*)>", kind) or re.fullmatch(r"&\[(.*)\]", kind)
    if match:
        inner = values(match.group(1), depth + 1)
        if not inner or depth > 1:
            return None
        small = inner[:3]
        items = [[]] + [[a] for a in small] + [[a, b] for a in small for b in small]
        return [("vec![" + ", ".join(i) + "]") if kind.startswith("Vec") else ("&[" + ", ".join(i) + "]") for i in items]
    match = re.fullmatch(r"Option<(.*)>", kind)
    if match:
        inner = values(match.group(1), depth + 1)
        return inner and ["None"] + [f"Some({v})" for v in inner[:4]]
    if kind.startswith("(") and kind.endswith(")"):
        parts, level, current = [], 0, ""
        for ch in kind[1:-1] + ",":
            if ch == "," and level == 0:
                parts.append(current)
                current = ""
                continue
            level += ch in "(<["
            level -= ch in ")>]"
            current += ch
        pools = [values(p, depth + 1) for p in parts if p.strip()]
        if not all(pools):
            return None
        return ["(" + ", ".join(c) + ")" for c in itertools.islice(itertools.product(*[p[:4] for p in pools]), 16)]
    return None


def candidates(params: list[tuple[str, str]], limit: int) -> list[dict] | None:
    pools = []
    for name, kind in params:
        pool = values(kind)
        if pool is None:
            return None
        pools.append((name, pool))
    rng = random.Random(SEED)
    size = 1
    for _, pool in pools:
        size *= len(pool)
    if size <= limit:
        chosen = list(itertools.product(*[p for _, p in pools]))
    else:
        # All-simple combinations first, then a seeded random spread.
        chosen = list(itertools.islice(itertools.product(*[p[:3] for _, p in pools]), limit // 2))
        while len(chosen) < limit:
            chosen.append(tuple(rng.choice(p) for _, p in pools))
    return [dict(zip([n for n, _ in pools], c)) for c in dict.fromkeys(chosen)]


def batch_file(harness: str, params, antecedent, consequent, picks) -> tuple[str, dict[str, dict]]:
    body, names = [], {}
    for i, pick in enumerate(picks):
        name = f"__free_{i}"
        names[name] = pick
        lets = [f"    let {'ghost ' if SPEC_ONLY.match(t) else ''}{n}: {t} = {pick[n]};" for n, t in params]
        goals = [f"        assert({c});" for c in antecedent] + [f"        assert(!{c});" for c in consequent]
        body.append(f"#[allow(unused_variables)]\nfn {name}() {{\n" + "\n".join(lets) + "\n    proof {\n" + "\n".join(goals) + "\n    }\n}\n")
    return harness + "\nverus! {\n" + "\n".join(body) + "} // free search\n", names


def search(harness_path: Path, limit: int) -> tuple[dict | None, int, str]:
    harness = harness_path.read_text()
    _, params, antecedent, consequent, _, _ = lemma_signature(harness)
    picks = candidates(params, limit)
    if picks is None:
        return None, 0, "unsupported type"
    text, names = batch_file(harness, params, antecedent, consequent, picks)
    with tempfile.TemporaryDirectory(prefix="free_") as directory:
        path = Path(directory) / "free.rs"
        path.write_text(text)
        flags = ["--verify-function", "__free_*"]
        try:
            run = subprocess.run([VERUS, "--crate-type=lib", "--verify-root", *flags, str(path)],
                                 capture_output=True, text=True, timeout=280)
        except subprocess.TimeoutExpired:
            return None, len(picks), "timeout"
    log = run.stdout + run.stderr
    if "verification results" not in log:
        return None, len(picks), "did not compile"
    lines = text.splitlines()
    starts = [(i + 1, re.match(r"fn (__free_\d+)", l).group(1)) for i, l in enumerate(lines) if re.match(r"fn __free_\d+", l)]
    failed = set()
    for number in re.findall(r"free\.rs:(\d+):", log):
        owner = [n for line, n in starts if line <= int(number)]
        if owner:
            failed.add(owner[-1])
    for name, pick in names.items():
        if name not in failed and refute(harness, pick).get("outcome") == "refuted":
            return pick, len(picks), "refuted"
    return None, len(picks), "no witness"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--clauses", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    with args.clauses.open() as stream:
        rows = list(csv.DictReader(stream))
    jobs = [(r, form) for r in rows for form in ("uncond", "guarded")
            if not (form == "guarded" and r["forms"] == "one") and (args.harness / r["id"] / f"{form}.rs").exists()]

    def work(job):
        row, form = job
        witness, tried, status = search(args.harness / row["id"] / f"{form}.rs", args.limit)
        return {"id": row["id"], "form": form, "status": status, "tried": tried, "witness": witness}

    with args.out.open("w") as stream, ThreadPoolExecutor(args.workers) as pool:
        for result in pool.map(work, jobs):
            stream.write(json.dumps(result) + "\n")
            stream.flush()


if __name__ == "__main__":
    main()
