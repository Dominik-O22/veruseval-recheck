"""Build one row per VeruSteer test tree: root program plus recorded default and VeruSteer outcomes.

    python3 -I extract_tests.py <VeruSteer repo> <out dir>
"""
import csv, hashlib, json, sys
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
(out / "roots").mkdir(parents=True, exist_ok=True)

def outcomes(name):
    rows = {}
    for line in (repo / "results/analysis" / name).open():
        r = json.loads(line)
        rows[r["tree_id"]] = r
    return rows

default, steer = outcomes("default_paths.jsonl"), outcomes("selector_paths.jsonl")
rows = {}
for pipeline in ("autoverus", "verusage"):
    for line in (repo / f"data/paths/test_{pipeline}.jsonl").open():
        r = json.loads(line)
        if r["tree_id"] in rows:
            continue
        root = r["path_states"][0]
        code = root["code_text"]
        digest = hashlib.sha256(code.encode()).hexdigest()[:16]
        (out / "roots" / f"{digest}.rs").write_text(code)
        k = r["tree_key"]
        rows[r["tree_id"]] = {
            "tree_id": r["tree_id"], "pipeline": pipeline, "task_id": k["task_name"],
            "dataset": k["dataset_name"], "gen_model": k["llm_name"], "shot": k["shot"],
            "root": digest, "root_score": root["score_tuple"], "root_types": "+".join(root["failure_types"]),
            "default_verified": default[r["tree_id"]]["label"], "steer_verified": steer[r["tree_id"]]["label"],
        }
with (out / "test_trees.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(next(iter(rows.values()))))
    w.writeheader(); w.writerows(rows.values())
vals = list(rows.values())
print(len(vals), "trees;", len({v["root"] for v in vals}), "distinct roots;", len({v["task_id"] for v in vals}), "tasks")
for p in ("autoverus", "verusage"):
    s = [v for v in vals if v["pipeline"] == p]
    print(p, len(s), "default", sum(v["default_verified"] for v in s), "steer", sum(v["steer_verified"] for v in s))
