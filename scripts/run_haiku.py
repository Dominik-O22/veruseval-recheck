"""Vibe check: run StarVerus few-shot with a Claude model (via the Agent SDK) on
tasks that fooled every original model, then re-evaluate it and the five
original StarVerus few-shot programs on the same tasks with the pinned evaluator.

Run inside the VerusEval container from the release root:
    python haiku/run_haiku.py --limit 5 --output-root runs/haiku-5
    python haiku/run_haiku.py --model claude-sonnet-5-5 --limit 5 --output-root runs/sonnet-5
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generation.run_starverus import UPSTREAM, runtime_config

GENERATION = ROOT / "data/generation"


def generate(tasks: list[dict], model: str, out: Path, workers: int) -> dict[str, Path]:
    """Run upstream StarVerus once per benchmark subset; return task_id -> final program."""
    config = runtime_config(os.environ.get("VERUS_PATH", "/opt/verus/verus"), model, "agent-sdk", "unused")
    config_path = out / "starverus.yaml"
    config_path.write_text(yaml.safe_dump(config))
    finals: dict[str, Path] = {}
    for subset in sorted({t["subset"] for t in tasks}):
        source = out / "input" / subset
        source.mkdir(parents=True)
        for task in (t for t in tasks if t["subset"] == subset):
            shutil.copy(GENERATION / "X_code" / subset / f"{task['task_id']}.rs", source)
        log = out / "logs" / f"{subset}.log"
        log.parent.mkdir(exist_ok=True)
        with log.open("w") as stream:
            subprocess.run([
                sys.executable, str(UPSTREAM), "--config", str(config_path),
                "--mode", "few-shot", "--model_name", "configured-model",
                "--source_bench_dir", str(source),
                "--x_dir", str(GENERATION / "X_code"), "--y_dir", str(GENERATION / "Y"),
                "--knn_json_path", str(GENERATION / "knn_similar.json"),
                "--result_save_path", str(out / "generation"),
                "--repair_save_path", str(out / "repair"),
                "--num_workers", str(workers),
            ], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
        for name, final in re.findall(
                r"\[TASK (?:VERIFIED|DONE)\] (.*?): generated=\d+, selected=(.*)", log.read_text()):
            finals[Path(name).stem] = Path(final.strip())
    return finals


def write_manifest(tasks: list[dict], label: str, finals: dict[str, Path], out: Path) -> Path:
    """The Claude model's finals plus the released StarVerus few-shot programs for the same tasks."""
    ids = {t["task_id"] for t in tasks}
    rows = [{"workflow": "StarVerus", "model": label, "shot": "few-shot", "task_id": task,
             "generated_path": str(path.resolve())} for task, path in sorted(finals.items())]
    with (ROOT / "data/generated/manifest.csv").open() as stream:
        rows += [{k: r[k] for k in ("workflow", "model", "shot", "task_id", "generated_path")}
                 for r in csv.DictReader(stream)
                 if r["workflow"] == "StarVerus" and r["shot"] == "few-shot" and r["task_id"] in ids]
    path = out / "programs.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--tasks", type=Path, default=ROOT / "haiku/tasks.csv")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = args.output_root.resolve()
    out.mkdir(parents=True, exist_ok=False)
    with args.tasks.open() as stream:
        tasks = list(csv.DictReader(stream))[: args.limit]
    os.environ.setdefault("AGENT_SDK_USAGE_LOG", str(out / "usage.jsonl"))

    finals = generate(tasks, args.model, out, args.workers)
    missing = sorted({t["task_id"] for t in tasks} - set(finals))
    print(f"generated {len(finals)}/{len(tasks)} tasks" + (f"; missing {missing}" if missing else ""))
    manifest = write_manifest(tasks, args.model.removeprefix("claude-"), finals, out)
    subprocess.run([sys.executable, "scripts/reevaluate.py", "dataset", "--manifest", str(manifest),
                    "-o", str(out / "eval"), "--workers", str(args.workers),
                    "--verus-path", os.environ.get("VERUS_PATH", "/opt/verus/verus")],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
