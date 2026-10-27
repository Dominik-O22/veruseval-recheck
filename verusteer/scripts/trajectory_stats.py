"""Statistics on VeruSteer's recorded test trajectories.

Reproduces the paper's verified counts, then reports how many test programs start out not
compiling, how many failed default trajectories never change the program, whether the verified
default trajectories pass lynette's code/contract check (root vs final program), and, if the
VeruSAGE tree edges are extracted, how often a repair round keeps the original program.

    python3 -I trajectory_stats.py <VeruSteer repo> <lynette binary>
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    repo, lynette = Path(sys.argv[1]), sys.argv[2]
    outcomes = {}
    for name in ("default_paths.jsonl", "selector_paths.jsonl"):
        for line in (repo / "results/analysis" / name).open():
            r = json.loads(line)
            if r["split"] == "test":
                outcomes.setdefault(r["tree_id"], {})[name] = r["label"]
    print(f"test trees {len(outcomes)}: default verified {sum(o['default_paths.jsonl'] for o in outcomes.values())}, "
          f"VeruSteer verified {sum(o['selector_paths.jsonl'] for o in outcomes.values())}")

    roots, never_changed, gate = Counter(), Counter(), Counter()
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.rs", Path(tmp) / "b.rs"
        for pipeline in ("autoverus", "verusage"):
            for line in (repo / f"data/paths/test_{pipeline}.jsonl").open():
                r = json.loads(line)
                if not r["default"]:
                    continue
                states = r["path_states"]
                compiles = states[0]["score_tuple"] != [-1, -1]
                roots[(compiles, r["label"])] += 1
                if not r["label"]:
                    never_changed[all(s["code_text"] == states[0]["code_text"] for s in states)] += 1
                else:
                    a.write_text(states[0]["code_text"])
                    b.write_text(states[-1]["code_text"])
                    gate[subprocess.run([lynette, "compare", "-t", a, b], capture_output=True).returncode == 0] += 1
    total = sum(roots.values())
    not_compiling = roots[(False, False)] + roots[(False, True)]
    print(f"roots that do not compile: {not_compiling}/{total} ({not_compiling / total:.1%}); "
          f"of those verified by the default rule: {roots[(False, True)]}")
    failed = sum(never_changed.values())
    print(f"failed default trajectories whose program never changes: {never_changed[True]}/{failed} "
          f"({never_changed[True] / failed:.1%})")
    print(f"verified default trajectories passing lynette compare -t (root vs final): {gate[True]}/{sum(gate.values())}")

    edges = repo / "data/trees/verusage/edges.jsonl"
    if edges.exists():
        kept = Counter()
        for line in edges.open():
            e = json.loads(line)
            kept[(e["source_score_tuple"] == [-1, -1], e["is_carry_forward_original"])] += 1
        for compiles, label in ((True, "non-compiling"), (False, "compiling")):
            n = kept[(compiles, True)] + kept[(compiles, False)]
            print(f"VeruSAGE repair rounds on {label} programs that keep the original: "
                  f"{kept[(compiles, True)]}/{n} ({kept[(compiles, True)] / n:.1%}), all splits")


if __name__ == "__main__":
    main()
