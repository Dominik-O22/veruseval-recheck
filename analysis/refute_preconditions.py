"""Show that a reference precondition really is stricter than a generated one, using Verus alone.

For each generated precondition => reference precondition check, this tries small inputs: lengths
0 to 2 for sequences and a few integers. An input counts when Verus proves it satisfies the
generated precondition and violates the reference's, so no model is involved. Each hit is re-run
with `ensures false`, which must fail, to catch a witness that holds only vacuously. Run with
--direction pre_ref_to_gen as a soundness control: checks that hold must yield no witness.

Run inside the VerusEval container from the release root:
    python haiku/refute_preconditions.py runs/haiku-fair20 runs/haiku-fair20-rest --label haiku-5-5
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import itertools
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adjudicate import capture_checks, verus

MAX_INPUTS = 40
LEMMA = re.compile(r"(proof fn lemma_\w+(?:<[^>]*>)?\((.*?)\)\s*requires\s*)(.*?)(\s*ensures\s*)(.*?)(\s*\{\s*\})", re.S)


def parameters(text: str) -> list[tuple[str, str]]:
    """Split a parameter list on top-level commas."""
    parts, depth, current = [], 0, ""
    for char in text:
        depth += char in "<(["
        depth -= char in ">)]"
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    return [tuple(s.strip() for s in p.split(":", 1)) for p in [*parts, current] if ":" in p]


def values(name: str, kind: str) -> list[str]:
    """Candidate constraints for one parameter; a sequence's contents stay universally quantified."""
    base = kind.replace("&", "").replace("mut ", "").strip()
    if base.startswith(("Vec<", "[", "Seq<")):
        return [f"{name}@.len() == {n}" for n in (0, 1, 2)]
    if re.fullmatch(r"[iu](8|16|32|64|128|size)", base):
        return [f"{name} == {v}" for v in ([-1] if base[0] == "i" else []) + [0, 1, 2, 101]]
    return [""]


def goal(harness: str, match: re.Match, constraint: str, ensures: str) -> str:
    return (harness[:match.start()] + match[1] + constraint + match[4] + ensures + match[6]
            + harness[match.end():])


def search(record: dict) -> str:
    """Return the first input that refutes the implication, or why there is none."""
    harness = record["harness"]
    match = LEMMA.search(harness)
    if not match:
        return "no lemma"
    antecedent = match[3].strip().rstrip(",")
    consequent = " && ".join(c.strip().rstrip(",") for c in match[5].splitlines() if c.strip())
    params = [values(n, k) for n, k in parameters(match[2]) if not n.startswith("__ret")]
    tried = 0
    for combination in itertools.islice(itertools.product(*params), MAX_INPUTS):
        constraint = ", ".join(c for c in combination if c)
        if not constraint:
            continue
        tried += 1
        if verus(goal(harness, match, constraint + ",", f"{antecedent},\n!({consequent}),"))[0]:
            vacuous = verus(goal(harness, match, constraint + ",", "false,"))[0]
            return f"{'vacuous' if vacuous else 'refuted'}: {constraint}"
    return f"no small witness in {tried} inputs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--label", help="Only programs with this model label (default: all).")
    parser.add_argument("--direction", default="pre_gen_to_ref")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        references = {r["task_id"]: r["reference_path"] for r in csv.DictReader(stream)}
    # capture_checks patches module globals, so harnesses are captured one at a time.
    checks = []
    for run in args.runs:
        with (run / "programs.csv").open() as stream:
            for program in csv.DictReader(stream):
                if args.label and program["model"] != args.label:
                    continue
                generated = Path(program["generated_path"].replace("/workspace/", ""))
                for record in capture_checks(generated, ROOT / references[program["task_id"]], {args.direction}):
                    checks.append((program["task_id"], record))
    with ThreadPoolExecutor(args.workers) as pool:
        for (task, record), outcome in zip(checks, pool.map(search, (r for _, r in checks))):
            print(f"{task:<34}{record['function']:<24}{str(record.get('status')):<9}{outcome}", flush=True)


if __name__ == "__main__":
    main()
