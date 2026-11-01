"""Do any results depend on the lynette ghost-only `if` bug?

Runs each tree's own pipeline check, root vs final program, with the lynette the paper's pipelines
used and with the fix from microsoft/verus-proof-synthesis#53. Covers every verified path in the
recorded test trees, then every program in the given 30-task runs, whose `accepted` verdicts it
recomputes as verified, passing the check and adding no bypass.

    python3 -I gate_recheck.py <VeruSteer repo> <old lynette> <fixed lynette> <roots dir> \
        <changed.csv> [<run dir>...]
"""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def passes(lynette: str, pipeline: str, a: Path, b: Path) -> bool:
    command = ["compare", "-t"] if pipeline == "autoverus" else ["additions"]
    return subprocess.run([lynette, *command, str(a), str(b)], capture_output=True).returncode == 0


def verified_paths(repo: Path) -> list[dict]:
    selected = {json.loads(l)["path_id"] for l in (repo / "results/analysis/selector_paths.jsonl").open()}
    rows = []
    for pipeline in ("autoverus", "verusage"):
        for line in (repo / f"data/paths/test_{pipeline}.jsonl").open():
            r = json.loads(line)
            if r["label"]:
                rows.append({"tree_id": r["tree_id"], "path_id": r["path_id"], "pipeline": pipeline,
                             "default": r["default"], "selected": r["path_id"] in selected,
                             "root": r["path_states"][0]["code_text"], "final": r["path_states"][-1]["code_text"]})
    return rows


def check_paths(repo: Path, old: str, fixed: str, changed_csv: Path) -> None:
    tally, changed = Counter(), []
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.rs", Path(tmp) / "b.rs"
        for row in verified_paths(repo):
            a.write_text(row["root"])
            b.write_text(row["final"])
            before, after = passes(old, row["pipeline"], a, b), passes(fixed, row["pipeline"], a, b)
            for group, member in (("all verified paths", True), ("default rule", row["default"]),
                                  ("VeruSteer", row["selected"])):
                if member:
                    tally[(group, row["pipeline"], before, after)] += 1
            if before != after:
                changed.append({k: row[k] for k in ("tree_id", "path_id", "pipeline", "default", "selected")}
                               | {"old": before, "fixed": after})
    for (group, pipeline, before, after), n in sorted(tally.items()):
        print(f"{group}\t{pipeline}\told {'pass' if before else 'fail'}\tfixed {'pass' if after else 'fail'}\t{n}")
    with changed_csv.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["tree_id", "path_id", "pipeline", "default", "selected",
                                                    "old", "fixed"])
        writer.writeheader()
        writer.writerows(changed)
    print(f"verdict changed on {len(changed)} verified paths, listed in {changed_csv}")


def check_run(run: Path, roots: Path, old: str, fixed: str) -> None:
    with (run / "sample.csv").open() as stream:
        pipelines = {r["task_id"] + "|" + r["gen_model"]: r for r in csv.DictReader(stream)}
    grades = json.loads((run / "grades.json").read_text())
    accepted = Counter()
    for grade in grades:
        row = pipelines[grade["task_id"] + "|" + grade["gen_model"]]
        original, program = roots / f"{row['root']}.rs", run / row["root"] / "program.rs"
        for name, lynette in (("old", old), ("fixed", fixed)):
            ok = grade["verified"] and grade["no_bypass_added"] and passes(lynette, row["pipeline"], original, program)
            accepted[name] += ok
            if name == "fixed" and ok != grade["accepted"]:
                print(f"  {run.name}: {row['task_id']} {row['pipeline']} accepted {grade['accepted']} -> {ok}")
    print(f"{run.name}: recorded {sum(g['accepted'] for g in grades)}, old {accepted['old']}, "
          f"fixed {accepted['fixed']} of {len(grades)}")


def main() -> None:
    repo, old, fixed, roots, changed_csv = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5])
    check_paths(repo, old, fixed, changed_csv)
    for run in sys.argv[6:]:
        check_run(Path(run), roots, old, fixed)


if __name__ == "__main__":
    main()
