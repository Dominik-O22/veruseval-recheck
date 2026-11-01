"""Gate 2 tier 0: no-model proof tactics on every regenerated harness.

Tries, in order, an empty body at the release's default rlimit, an empty body at --rlimit 100, and
reveal_with_fuel(f, 8) for every recursive spec fn in the harness. Stops at the first proof.
Output rows keyed by item id and form. No model calls.

    python3 -I analysis/gate2_tier0.py --harness /work/harness --regen /work/regen.jsonl --out tier0.jsonl
"""
import argparse
import json
from multiprocessing import Pool
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate2_check import prove  # noqa: E402

ROOT = None


def tactics(harness: str):
    yield "empty", "// ---- body\n", None
    yield "rlimit100", "// ---- body\n", "100"
    recursive = list(dict.fromkeys(re.findall(r"spec fn (\w+)[^{;]*?decreases", harness, re.S)))
    if recursive:
        yield "fuel8", "// ---- body\n" + "\n".join(f"reveal_with_fuel({f}, 8);" for f in recursive), "100"


def work(job):
    item, form = job
    harness = (Path(ROOT) / item / f"{form}.rs").read_text()
    tries = []
    for name, proof, rlimit in tactics(harness):
        r = prove(harness, proof, rlimit)
        tries.append({"tactic": name, "outcome": r["outcome"], "seconds": r.get("seconds")})
        if r["outcome"] == "proved":
            break
    return {"id": item, "form": form, "tier0": tries[-1]["outcome"] == "proved",
            "by": tries[-1]["tactic"] if tries[-1]["outcome"] == "proved" else None, "tries": tries}


def main():
    global ROOT
    p = argparse.ArgumentParser()
    p.add_argument("--harness", required=True); p.add_argument("--regen", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True); p.add_argument("--workers", type=int, default=4)
    a = p.parse_args(); ROOT = a.harness
    jobs = []
    for line in a.regen.read_text().splitlines():
        row = json.loads(line)
        for form in ("uncond", "guarded"):
            if (Path(ROOT) / row["id"] / f"{form}.rs").exists():
                jobs.append((row["id"], form))
    with a.out.open("w") as w, Pool(a.workers) as pool:
        for r in pool.imap_unordered(work, jobs):
            w.write(json.dumps(r) + "\n"); w.flush()


if __name__ == "__main__":
    main()
