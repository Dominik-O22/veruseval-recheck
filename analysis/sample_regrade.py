"""Draw the re-grade sample from the paper's own flagged artifacts.

Pool: accepted artifacts from the strong models (DeepSeek-Chat, DeepSeek-Reasoner,
Qwen3-Coder) whose reliability check failed ("weaker than the reference"), on
tasks outside the broken list. Draws 15 from the largest spec-size tercile and
15 from the smallest, at most one artifact per task, with a fixed seed.

Writes <run>/programs.csv and copies the released per-file records into
<run>/eval/per_file so adjudicate.py and verdicts.py can run on them.

    python analysis/sample_regrade.py --release . --tasks results/tasks --run runs/regrade-30
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import random
import shutil

STRONG = {"deepseek-reasoner", "deepseek-chat", "qwen-coder"}
SEED = 20261026


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("."))
    parser.add_argument("--tasks", type=Path, default=Path("results/tasks"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--per-group", type=int, default=15)
    args = parser.parse_args()
    root = args.release
    with (root / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        labels = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True"]
    with (root / "data/generated/manifest.csv").open() as stream:
        manifest = {r["sample_id"]: r for r in csv.DictReader(stream)}
    broken = set((args.tasks / "broken_tasks.txt").read_text().split())
    pool = [r for r in labels if r["model"] in STRONG and r["verification_stage"] == "accepted"
            and r["formal_reliability_state"] == "unfavorable" and r["task_id"] not in broken
            and r["spec_node_count"]]
    size = lambda r: float(r["spec_node_count"])
    ordered = sorted(map(size, pool))
    low, high = ordered[len(ordered) // 3], ordered[2 * len(ordered) // 3]

    rng, taken = random.Random(SEED), set()

    def draw(group: list[dict]) -> list[dict]:
        picked = []
        for row in rng.sample(group, len(group)):
            if row["task_id"] not in taken:
                picked.append(row)
                taken.add(row["task_id"])
            if len(picked) == args.per_group:
                break
        return picked

    groups = {"big": draw([r for r in pool if size(r) >= high]),
              "small": draw([r for r in pool if size(r) <= low])}
    (args.run / "eval" / "per_file").mkdir(parents=True, exist_ok=False)
    with (args.run / "programs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["workflow", "model", "shot", "task_id",
                                                    "generated_path", "size_group"])
        writer.writeheader()
        for group, rows in groups.items():
            for row in rows:
                entry = manifest[row["sample_id"]]
                writer.writerow({k: entry[k] for k in ("workflow", "model", "shot", "task_id", "generated_path")}
                                | {"size_group": group})
                shutil.copy(root / entry["result_path"], args.run / "eval" / "per_file")
    print(f"pool {len(pool)}; size cut-offs <= {low:.0f} / >= {high:.0f}; sampled "
          f"{sum(map(len, groups.values()))} into {args.run}")


if __name__ == "__main__":
    main()
