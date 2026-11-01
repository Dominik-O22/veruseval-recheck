"""Gate 2 checker: turn a proof or a literal witness into a Verus verdict for a regenerated lemma.

Harnesses come from analysis/gate2_regenerate.py and embed the release's references, so they are
read from outside the repository and never written into it. Only a positive Verus result is a
verdict; a timeout or a failed attempt is reported as "failed" and is never a verdict.

prove:  splice helpers before the unchanged lemma and the body into its empty braces, reject
        forbidden constructs, verify the WHOLE file (so helpers are checked too).
        python3 -I analysis/gate2_check.py prove HARNESS.rs PROOF.rs [--rlimit N]
        PROOF.rs holds two sections, separated by a line `// ---- body`: helpers, then body.

refute: the proposer gives literal values only (JSON: {"__arg0": "vec![1i32, 2]", "__ret0": "true"},
        optional "_fuel": {"spec_fn_name": 4}). A fixed template binds them in an exec fn with no
        loops, branches or calls, and asserts every antecedent wrapper and the negated consequent.
        Exec construction means the witness is a real, representable value. The same file with
        `assert(false)` instead is also run: if that verifies the context is inconsistent and the
        verdict is void.
        python3 -I analysis/gate2_check.py refute HARNESS.rs WITNESS.json
Prints one JSON line with the outcome.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERUS = os.environ.get("VERUS_PATH", "/opt/verus/verus")
FORBIDDEN = ("assume", "admit", "external_body", "external_fn", "external", "#[verifier", "#![verifier",
             "axiom", "uninterp", "unsafe", "opaque", "trusted")
LITERAL_FORBIDDEN = re.compile(r"\b(if|else|while|for|loop|match|let|fn|assume|admit|unsafe|proof|spec|choose|forall|exists)\b|[;=|]")
SPEC_ONLY = re.compile(r"^(int|nat|Seq<.*|Set<.*|Map<.*|Multiset<.*|spec_fn.*)$")
TIMEOUT = 300


def run_verus(text: str, extra: list[str]) -> tuple[str, str, float]:
    with tempfile.TemporaryDirectory(prefix="gate2_") as directory:
        path = Path(directory) / "gate2.rs"
        path.write_text(text)
        start = time.monotonic()
        try:
            out = subprocess.run([VERUS, "--crate-type=lib", *extra, str(path)], capture_output=True,
                                 text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return "timeout", "", time.monotonic() - start
        log = out.stdout + out.stderr
        ok = out.returncode == 0 and re.search(r"verification results:: \d+ verified, 0 errors", log)
        return ("verified" if ok else "failed"), log, time.monotonic() - start


def lemma_signature(harness: str) -> tuple[str, list[tuple[str, str]], list[str], list[str], int, int]:
    match = re.search(r"proof fn (lemma_sqm_\w+)\s*(<[^>]*>)?\s*\(", harness)
    name = match.group(1)
    depth, i = 1, match.end()
    while depth:
        depth += {"(": 1, ")": -1}.get(harness[i], 0)
        i += 1
    params_text = harness[match.end():i - 1]
    params, depth, current = [], 0, ""
    for ch in params_text + ",":
        if ch == "," and depth == 0:
            if current.strip():
                n, t = current.split(":", 1)
                params.append((n.strip(), t.strip()))
            current = ""
            continue
        depth += {"<": 1, "(": 1, "[": 1, ">": -1, ")": -1, "]": -1}.get(ch, 0)
        current += ch
    body_open = harness.index("{", i)
    body_close = harness.index("}", body_open)
    header = harness[i:body_open]
    req = re.search(r"requires(.*?)(ensures|$)", header, re.S)
    ens = re.search(r"ensures(.*)$", header, re.S)
    calls = lambda s: [c.strip() for c in re.findall(r"(__sqm_\w+\([^()]*\))", s or "")]
    return name, params, calls(req and req.group(1)), calls(ens and ens.group(1)), body_open, body_close


def prove(harness: str, proof: str, rlimit: str | None) -> dict:
    helpers, _, body = proof.partition("// ---- body")
    if any(word in proof for word in FORBIDDEN):
        return {"outcome": "rejected", "reason": "forbidden construct",
                "hits": [w for w in FORBIDDEN if w in proof]}
    name, _, _, _, body_open, body_close = lemma_signature(harness)
    if harness[body_open + 1:body_close].strip():
        return {"outcome": "rejected", "reason": "lemma body not empty"}
    start = harness.index(f"proof fn {name}")
    text = harness[:start] + helpers.strip() + "\n\n" + harness[start:body_open + 1] + "\n" + body.strip() + "\n" + harness[body_close:]
    # Statement must be unchanged: everything up to the body is byte-identical after the helpers.
    assert text[text.index(f"proof fn {name}"):].startswith(harness[start:body_open + 1])
    status, log, seconds = run_verus(text, ["--rlimit", rlimit] if rlimit else [])
    tail = "\n".join(l for l in log.splitlines() if "error" in l or "verification results" in l)[-1500:]
    return {"outcome": "proved" if status == "verified" else status, "seconds": round(seconds, 1), "log": tail}


def literal_ok(value: str) -> bool:
    if LITERAL_FORBIDDEN.search(value.replace("=>", " ")):
        return False
    for m in re.finditer(r"([A-Za-z_][\w:]*)\s*(!?)\s*\(", value):
        word, bang = m.group(1), m.group(2)
        if not (word.split("::")[-1][:1].isupper() or (bang and word in ("vec", "seq", "map", "set"))):
            return False  # only constructors such as Some(..) and vec!/seq! literals
    return True


def refute(harness: str, witness: dict) -> dict:
    name, params, antecedent, consequent, _, _ = lemma_signature(harness)
    fuel = witness.get("_fuel", {})
    types = witness.get("_types", {})  # instantiate a generic lemma: one bad instance refutes it
    if not all(re.fullmatch(r"\w+", k) and literal_ok(v) and re.fullmatch(r"[\w<>, ()&\[\]]+", v)
               for k, v in types.items()):
        return {"outcome": "rejected", "reason": "bad _types"}
    for k, v in types.items():
        params = [(n, re.sub(rf"\b{k}\b", v, t)) for n, t in params]
    missing = [n for n, _ in params if n not in witness]
    if missing:
        return {"outcome": "rejected", "reason": f"missing values for {missing}"}
    for n, _ in params:
        if not literal_ok(str(witness[n])):
            return {"outcome": "rejected", "reason": f"{n} is not a literal: {witness[n]}"}
    if not all(re.fullmatch(r"\w+", f) and isinstance(k, int) for f, k in fuel.items()):
        return {"outcome": "rejected", "reason": "bad fuel"}
    lets = []
    for n, t in params:
        ghost = "ghost " if SPEC_ONLY.match(t) else ""
        lets.append(f"    let {ghost}{n}: {t} = {witness[n]};")
    reveal = [f"        reveal_with_fuel({f}, {k});" for f, k in fuel.items()]
    goals = [f"        assert({c});" for c in antecedent] + [f"        assert(!{c});" for c in consequent]

    def file_with(asserts: list[str]) -> str:
        fn = ("\n#[allow(unused_variables)]\nfn __gate2_witness() {\n" + "\n".join(lets) + "\n    proof {\n"
              + "\n".join(reveal + asserts) + "\n    }\n}\n")
        # A second verus! block at the end of the file; harnesses do not all mark the end of theirs.
        return harness + "\nverus! {\n" + fn + "} // gate2 witness\n"

    flags = ["--verify-root", "--verify-function", "__gate2_witness"]
    status, log, seconds = run_verus(file_with(goals), flags)
    vacuity, vlog, _ = run_verus(file_with(["        assert(false);"]), flags)
    tail = "\n".join(l for l in log.splitlines() if "error" in l or "verification results" in l)[-1500:]
    if status == "verified" and vacuity == "verified":
        return {"outcome": "void", "reason": "assert(false) also verifies", "seconds": round(seconds, 1)}
    return {"outcome": "refuted" if status == "verified" else status, "vacuity": vacuity,
            "seconds": round(seconds, 1), "log": tail}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("prove", "refute", "sig"))
    parser.add_argument("harness", type=Path)
    parser.add_argument("attempt", type=Path, nargs="?")
    parser.add_argument("--rlimit")
    args = parser.parse_args()
    harness = args.harness.read_text()
    if args.mode == "sig":
        name, params, a, c, _, _ = lemma_signature(harness)
        print(json.dumps({"lemma": name, "params": params, "antecedent": a, "consequent": c}))
        return
    attempt = args.attempt.read_text()
    result = prove(harness, attempt, args.rlimit) if args.mode == "prove" else refute(harness, json.loads(attempt))
    print(json.dumps({"mode": args.mode, "harness": str(args.harness), "attempt": str(args.attempt), **result}))


if __name__ == "__main__":
    main()
