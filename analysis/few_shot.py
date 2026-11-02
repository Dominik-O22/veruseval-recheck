"""What the few-shot examples carry. No model calls, no Verus. Every few-shot figure in the plan comes from here.

Writes few_shot.json, and two task lists used as sensitivity checks:
    twin_tasks.txt            a neighbour has an identical contract, 40 characters or longer
    prose_neighbour_tasks.txt a neighbour's solution carries task-like comments

    python3 -I analysis/few_shot.py --release REL --out results/part_a --tasks-out results/tasks
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from broken_tasks import spec_text

PROSE = re.compile(r"//\s*(Write|Given|Return|Returns|Find|Check|Compute|This function|Function:|Task|Problem|Determine|Count)\b", re.I)
NUMBER = re.compile(r"(?<![\w.])\d+(?![\w.])")


def normal(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"//[^\n]*", "", text)).strip()


def rate(pairs: list[tuple[bool, bool]]) -> dict:
    return {"pairs": len(pairs), "without_examples": round(sum(z for _, z in pairs) / len(pairs) * 100, 1),
            "with_examples": round(sum(f for f, _ in pairs) / len(pairs) * 100, 1)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tasks-out", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = args.release
    hidden = set((repo / "results/tasks/hidden_constant_tasks.txt").read_text().split())
    knn = json.loads((root / "data/generation/knn_similar.json").read_text())
    solutions = {p.stem: p.read_text() for p in (root / "data/generation/Y").glob("*/*.rs")}
    inputs = {p.stem: p.read_text() for p in (root / "data/generation/X_code").glob("*/*.rs")}
    references = {p.stem: p.read_text() for p in (root / "data/references").glob("*/*.rs")}
    contracts = {t: normal(spec_text(s)) for t, s in solutions.items()}
    twins = sorted(t for t, near in knn.items() if len(contracts[t]) >= 40 and any(contracts[n] == contracts[t] for n in near))
    prose = {t for t, s in solutions.items() if PROSE.search(s)}
    prose_neighbours = sorted(t for t, near in knn.items() if any(n in prose for n in near))
    identical = sum(normal(solutions[t]) == normal(references[t]) for t in solutions if t in references)
    shown = reached = 0
    for task in hidden:
        wanted = {n for n in NUMBER.findall(spec_text(references[task])) if int(n) > 2} - set(NUMBER.findall(inputs[task]))
        if wanted:
            shown += 1
            examples = "\n".join(solutions[n] for n in knn[task])
            reached += wanted <= set(NUMBER.findall(examples))
    with (root / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        labels = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True" and r["verification_stage"] == "accepted"]
    with (root / "data/evaluation/rq1_artifact_outcomes.csv").open() as stream:
        outcomes = {r["sample_id"]: r for r in csv.DictReader(stream)}
    groups: dict[tuple, dict] = defaultdict(dict)
    for row in labels:
        groups[(row["workflow"], row["model"], row["task_id"])][row["shot"]] = row
    pairs = [(k, v["few-shot"], v["zero-shot"]) for k, v in groups.items() if len(v) == 2]
    report: dict = {"solutions_identical_to_reference": identical, "twin_tasks": len(twins), "tasks_with_prose_neighbour": len(prose_neighbours),
                    "solutions_with_task_like_comments": len(prose),
                    "hidden_constant_tasks_with_constants": shown, "all_constants_in_examples_upper_bound": reached}
    for name, column in (("L1", "pre_ref_to_gen"), ("L2", "post_gen_to_ref"), ("L3", "pre_gen_to_ref"), ("L4", "post_ref_to_gen")):
        rejected = lambda row: outcomes[row["sample_id"]][column] == "invalid"
        report[f"rejected_{name}"] = {"all": rate([(rejected(f), rejected(z)) for _, f, z in pairs]),
                                      "hidden": rate([(rejected(f), rejected(z)) for k, f, z in pairs if k[2] in hidden]),
                                      "other": rate([(rejected(f), rejected(z)) for k, f, z in pairs if k[2] not in hidden])}
    clean = lambda row: row["formal_completeness_state"] == "favorable"
    star = [(k, f, z) for k, f, z in pairs if k[0] == "StarVerus"]
    report["starverus_L3_L4_clean"] = {"hidden": rate([(clean(f), clean(z)) for k, f, z in star if k[2] in hidden]),
                                       "other": rate([(clean(f), clean(z)) for k, f, z in star if k[2] not in hidden])}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "few_shot.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.tasks_out / "twin_tasks.txt").write_text("\n".join(twins) + "\n")
    (args.tasks_out / "prose_neighbour_tasks.txt").write_text("\n".join(prose_neighbours) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
