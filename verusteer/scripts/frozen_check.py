"""How many VeruSteer test failures are unfixable by construction?

The repair pipelines may only change ghost code: `lynette compare -t` rejects any candidate whose
executable code, requires/ensures or function decreases differ from the input. For
each non-compiling test root, this builds the frozen skeleton (the input with all ghost code
removed and spec fns kept, via a patched lynette), confirms the gate sees it as unchanged, and runs
Verus on it. If the skeleton's frontend fails, no proof-only edit can make the program compile.
AutoVerus's gate does not freeze spec fns, so its errors inside spec fns count as editable.

    python3 -I frozen_check.py <VeruSteer repo> <out dir>
"""
from __future__ import annotations

from collections import Counter
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
LYNETTE = str(HERE / "lynette/target/release/lynette")
IMAGE = "veruseval:agent"


def lynette(*args: str, skeleton: bool = False) -> subprocess.CompletedProcess:
    env = os.environ | ({"LYNETTE_SKELETON": "1"} if skeleton else {})
    return subprocess.run([LYNETTE, "compare", "-t", *args], capture_output=True, text=True, env=env)


def default_trees(repo: Path) -> list[dict]:
    rows = []
    for pipeline in ("autoverus", "verusage"):
        for line in (repo / f"data/paths/test_{pipeline}.jsonl").open():
            r = json.loads(line)
            if r["default"]:
                root = r["path_states"][0]
                rows.append({"tree_id": r["tree_id"], "pipeline": pipeline, "verified": r["label"],
                             "root_code": root["code_text"], "root_compiles": root["score_tuple"] != [-1, -1],
                             "root_error": next((l for l in root["verus_output_full"].splitlines()
                                                 if l.startswith("error")), "")})
    return rows


def build(rows: list[dict], work: Path) -> dict[str, str]:
    """Write each non-compiling root's skeleton; return a status per root file for the ones that fail early."""
    early = {}
    for i, row in enumerate(rows):
        if row["root_compiles"]:
            continue
        name = f"r{i}"
        root, skel = work / f"{name}.rs", work / f"skel_{name}.rs"
        root.write_text(row["root_code"])
        out = lynette(str(root), str(root), skeleton=True)
        if out.returncode != 0:
            early[name] = "lynette cannot parse root"
            continue
        skel.write_text(out.stdout)
        if lynette(str(root), str(skel)).returncode != 0:
            early[name] = "construction failed"
            skel.unlink()
            continue
        if not re.search(r"\bfn\s+main\s*\(", out.stdout):
            skel.write_text(out.stdout + "\nfn main() {}\n")
        row["name"] = name
    return early


def compile_all(work: Path) -> None:
    """Run Verus on every skeleton in one container; frontend success shows as a results line."""
    script = ('ls skel_*.rs | xargs -P 8 -I{} sh -c '
              '"timeout 180 verus --rlimit 1 {} > {}.out 2>&1; echo exit=\\$? >> {}.out"')
    subprocess.run(["podman", "run", "--rm", "-v", f"{work.resolve()}:/work:Z", "-w", "/work", IMAGE,
                    "sh", "-c", script], check=True)


def error_in_spec_fn(skeleton: Path, verus_output: str) -> list[bool]:
    """For each error location Verus reports, whether it is in a spec fn (one item per line in the skeleton)."""
    lines = skeleton.read_text().splitlines()
    return [bool(re.search(r"\bspec\s+fn\b", lines[int(n) - 1].split("{")[0]))
            for n in re.findall(rf"--> {re.escape(skeleton.name)}:(\d+):", verus_output) if int(n) <= len(lines)]


def main() -> None:
    repo, out = Path(sys.argv[1]), Path(sys.argv[2])
    work = out / "skeletons"
    work.mkdir(parents=True, exist_ok=True)
    rows = default_trees(repo)
    early = build(rows, work)
    compile_all(work)

    tally, records = Counter(), []
    for i, row in enumerate(rows):
        name = f"r{i}"
        uncertain = ""
        if row["root_compiles"]:
            status, first = "root compiles", ""
        elif name in early:
            status, first = early[name], row["root_error"]
        else:
            text = (work / f"skel_{name}.rs.out").read_text()
            if "verification results::" in text:
                status, first = "only ghost code broken", ""
            else:
                first = next((l for l in text.splitlines() if l.startswith("error")), text[-200:])
                status = "frozen code broken"
                in_spec = error_in_spec_fn(work / f"skel_{name}.rs", text)
                # AutoVerus's gate ignores spec fns; VeruSAGE's freezes them. Classify by the first
                # error (validated: no verified root lands in an unfixable bucket), and flag cases
                # with later errors outside spec fns, which may be cascades or real frozen errors.
                if row["pipeline"] == "autoverus" and in_spec and in_spec[0]:
                    status = "spec fn broken (editable)"
                    if not all(in_spec):
                        uncertain = "also has errors outside spec fns (may be cascades)"
        tally[(row["pipeline"], "verified" if row["verified"] else "failed", status)] += 1
        records.append({"tree_id": row["tree_id"], "pipeline": row["pipeline"], "verified": row["verified"],
                        "status": status, "skeleton_error": first, "root_error": row["root_error"],
                        "uncertain": uncertain})
    with (out / "frozen_check.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    for key, n in sorted(tally.items()):
        print(*key, n, sep="\t")
    failed = [r for r in records if not r["verified"]]
    unfixable = sum(r["status"] in ("frozen code broken", "lynette cannot parse root") for r in failed)
    uncertain = sum(bool(r["uncertain"]) for r in failed)
    print(f"failed {len(failed)}: unfixable {unfixable}, plus up to {uncertain} uncertain; verified roots "
          f"classified unfixable: {sum(r['status'] in ('frozen code broken', 'lynette cannot parse root') for r in records if r['verified'])}")


if __name__ == "__main__":
    main()
