"""Re-run L2 in the paper's unconditional form, with no model calls.

The evaluator's semantic_strength.py adds both preconditions to the antecedent of L2, while the
released labels use no premises. Mount a copy with the antecedent reduced over the release, then
run this in the container from the release root:

    sed 's/antecedent=ground_requires + gen_requires + gen_ensures,/antecedent=gen_ensures,/' \\
        metrics_rebuild/share/semantic_strength.py > /tmp/semantic_strength_uncond.py
    podman run --rm -v "$PWD":/workspace -w /workspace \\
        -v /tmp/semantic_strength_uncond.py:/workspace/metrics_rebuild/share/semantic_strength.py:ro \\
        veruseval:haiku python haiku/unconditional_l2.py --dump /workspace/runs/uncond-harnesses
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adjudicate import capture_checks

RUNS = (("regrade-30", None), ("haiku-5", "haiku-5-5"), ("haiku-hard-1", "haiku-5-5"),
        ("haiku-fair20", "haiku-5-5"), ("haiku-fair20-rest", "haiku-5-5"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, help="Write each rejected harness here.")
    args = parser.parse_args()
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        references = {r["task_id"]: r["reference_path"] for r in csv.DictReader(stream)}
    with (ROOT / "data/evaluation/rq1_artifact_outcomes.csv").open() as stream:
        released = {r["sample_id"]: r["post_gen_to_ref"] for r in csv.DictReader(stream)}
    for run, label in RUNS:
        with (ROOT / "runs" / run / "programs.csv").open() as stream:
            programs = [p for p in csv.DictReader(stream) if not label or p["model"] == label]
        for program in programs:
            generated = Path(program["generated_path"].replace("/workspace/", ""))
            sample = "|".join(program[k] for k in ("workflow", "model", "shot", "task_id"))
            for record in capture_checks(generated, ROOT / references[program["task_id"]], {"post_gen_to_ref"}):
                print(json.dumps({"run": run, "task": program["task_id"], "model": program["model"],
                                  "function": record.get("function"), "status": record.get("status"),
                                  "released": released.get(sample)}), flush=True)
                if args.dump and record.get("status") != "valid":
                    args.dump.mkdir(parents=True, exist_ok=True)
                    (args.dump / f"{program['task_id']}__{record['function']}.rs").write_text(record["harness"])


if __name__ == "__main__":
    main()
