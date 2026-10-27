"""Run VeruSteer's own repair pipeline (AutoVerus or VeruSAGE, default selection rule) with a Claude model.

Each task runs in one container: sdk_proxy.py serves the pipeline's OpenAI calls from the Claude
Agent SDK, and the pipeline's main.py runs exactly as VeruSteer's scripts/run_pipeline.py invokes it
(--repair 5). The config keeps the model name deepseek-chat, so their client makes one completion
per call as in the recorded runs. Output: <out>/<root>/{program.rs, pipeline.log, usage.jsonl}, with
program.rs the pipeline's final program, so run_agent.py grade can score it.

    python3 -I run_pipeline.py runs/fixable-5.csv --model claude-haiku-5-5 --out runs/pipe-haiku
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
IMAGE = "veruseval:pipeline"
CONFIG = {
    "use_openai": True, "single_completion_only": True, "force_single_completion": True,
    "aoai_api_base": ["http://127.0.0.1:8765/v1"], "aoai_api_key": ["unused"],
    "aoai_generation_model": "deepseek-chat", "aoai_debug_model": "deepseek-chat",
    "aoai_api_version": "2024-10-21", "aoai_max_retries": 5, "max_token": 4096,
    "debug_max_attempt": 3, "debug_temp": 1.0, "verus_path": "/opt/verus/verus",
    "example_path": "/pipe/repair/autoverus/examples", "lemma_path": "/pipe/repair/autoverus/lemmas",
    "util_path": "/pipe/repair/utils",
    # VeruSAGE reads these via getattr(config, key, default), but its config dict raises KeyError
    # rather than AttributeError, so missing keys crash every model-backed repair action. Set the
    # intended defaults explicitly.
    "fvt_mode": False, "fvt_prompt_supplement": "", "verus_args": [],
}


def token() -> str:
    """The subscription access token, read at run time and passed only through the environment."""
    creds = json.loads((Path.home() / ".claude/.credentials.json").read_text())
    return creds["claudeAiOauth"]["accessToken"]


def repair(row: dict, model: str, out: Path, timeout: int) -> None:
    work = out / row["root"]
    if (work / "program.rs").exists():
        return
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "roots" / f"{row['root']}.rs", work / "input.rs")
    (work / "config.json").write_text(json.dumps(CONFIG))
    pipeline = row["pipeline"]
    main = (f"cd /pipe/repair/{pipeline} && timeout {timeout} python main.py --config /work/config.json "
            f"--input /work/input.rs --output /work/repaired.rs --outdir /work/intermediate --repair 5"
            + (" --mode repair" if pipeline == "autoverus" else ""))
    script = (f"python /steer/sdk_proxy.py 8765 2>/work/proxy.err & sleep 2; {main} > /work/pipeline.log 2>&1;"
              " echo exit=$? >> /work/pipeline.log")
    start = time.time()
    subprocess.run(["podman", "run", "--rm", "-e", "CLAUDE_CODE_OAUTH_TOKEN", "-e", f"PROXY_MODEL={model}",
                    "-e", "PROXY_USAGE_LOG=/work/usage.jsonl", "-e", "CARGO_HOME=/cargo-home",
                    "-v", f"{work.resolve()}:/work:Z", "-v", f"{(HERE / 'pipe').resolve()}:/pipe:z",
                    "-v", f"{(HERE / 'cargo-home').resolve()}:/cargo-home:z",
                    "-v", f"{HERE}:/steer:ro,z", IMAGE, "sh", "-c", script],
                   env=os.environ | {"CLAUDE_CODE_OAUTH_TOKEN": token()})
    final = work / "repaired.rs"
    shutil.copy(final if final.exists() else work / "input.rs", work / "program.rs")
    (work / "agent.json").write_text(json.dumps({
        "tree_id": row["tree_id"], "model": f"{pipeline}+{model}", "exit": 0 if final.exists() else 1,
        "seconds": round(time.time() - start), "stderr": ""}))
    calls = len((work / "usage.jsonl").read_text().splitlines()) if (work / "usage.jsonl").exists() else 0
    print(f"{row['task_id']}: {pipeline} finished in {time.time() - start:.0f}s, {calls} model calls", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()
    with args.sample.open() as stream:
        rows = list(csv.DictReader(stream))
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.sample, args.out / "sample.csv")
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(lambda r: repair(r, args.model, args.out, args.timeout), rows))


if __name__ == "__main__":
    main()
