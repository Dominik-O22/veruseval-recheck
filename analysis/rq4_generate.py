"""RQ4: run StarVerus few-shot with a current model on a task list, once per task.

Same upstream pipeline and prompts as the release's StarVerus runs, through the Agent SDK adapter in
patches/starverus-agent-sdk.patch. Run in the container from the release root, with ANTHROPIC_API_KEY set:

    python3 -I analysis/rq4_generate.py --tasks results/tasks/rq4_tasks.txt --out DIR
Writes DIR/finals.jsonl, one row per task that produced a final program: {"task", "generated"}.

For RQ5, --text adds each task's description as comments at the top of the input, and nothing else changes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml

ROOT = Path("/workspace")
sys.path.insert(0, str(ROOT))

from scripts.generation.run_starverus import UPSTREAM, runtime_config  # noqa: E402

GENERATION = ROOT / "data/generation"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--text", type=Path, help="JSONL of {task, text}")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AGENT_SDK_USAGE_LOG", str(out / "usage.jsonl"))
    config = out / "starverus.yaml"
    config.write_text(yaml.safe_dump(runtime_config("/opt/verus/verus", args.model, "agent-sdk", "unused")))
    text = {r["task"]: r["text"] for r in map(json.loads, args.text.read_text().splitlines())} if args.text else {}
    subsets: dict[str, list[str]] = {}
    for task in args.tasks.read_text().split():
        subset = next(p.parent.name for p in GENERATION.glob(f"X_code/*/{task}.rs"))
        subsets.setdefault(subset, []).append(task)
    finals = {}
    for subset, tasks in sorted(subsets.items()):
        source = out / "input" / subset
        source.mkdir(parents=True, exist_ok=True)
        for task in tasks:
            target = source / f"{task}.rs"
            shutil.copy(GENERATION / "X_code" / subset / f"{task}.rs", target)
            if text:
                comment = "".join(f"// {line}\n" for line in ["Task description:", *text[task].splitlines()])
                target.write_text(comment + target.read_text())
        log = out / "logs" / f"{subset}.log"
        log.parent.mkdir(exist_ok=True)
        with log.open("w") as stream:
            subprocess.run([sys.executable, str(UPSTREAM), "--config", str(config), "--mode", "few-shot",
                            "--model_name", "configured-model", "--source_bench_dir", str(source),
                            "--x_dir", str(GENERATION / "X_code"), "--y_dir", str(GENERATION / "Y"),
                            "--knn_json_path", str(GENERATION / "knn_similar.json"),
                            "--result_save_path", str(out / "generation"), "--repair_save_path", str(out / "repair"),
                            "--num_workers", str(args.workers)], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
        for name, final in re.findall(r"\[TASK (?:VERIFIED|DONE)\] (.*?): generated=\d+, selected=(.*)", log.read_text()):
            finals[Path(name).stem] = final.strip()
    (out / "finals.jsonl").write_text("".join(json.dumps({"task": t, "generated": p}) + "\n" for t, p in sorted(finals.items())))
    print(len(finals), "finals from", sum(map(len, subsets.values())), "tasks")


if __name__ == "__main__":
    main()
