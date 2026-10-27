"""Repair VeruSteer test programs with a tool-using agent, graded by the pipelines' own rules.

Each sampled test tree's root program (a failing DeepSeek-Chat/Qwen-Coder generation) goes to an
agent that can run Verus itself. The result counts only if Verus verifies it, it passes the
tree's own pipeline check (AutoVerus: lynette compare -t, which freezes executable code and
requires/ensures/function decreases; VeruSAGE: lynette additions, which also freezes spec fns), and
no assume, admit or external_body was added. Grades also report a tolerant variant that
ignores `use` lines and trigger annotations and a stricter one that pins spec fns.

    python3 -I run_agent.py sample --n 5 --seed 1 --out runs/sample-5.csv
    python3 -I run_agent.py run runs/sample-5.csv --model opencode/deepseek-v4.1-flash-free --out runs/ds-flash
    python3 -I run_agent.py grade runs/ds-flash
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
LYNETTE = HERE / "lynette/target/release/lynette"
IMAGE = "veruseval:agent"
FORBIDDEN = ("admit()", "assume(", "#[verifier::external_body]", "#[verifier::admit]")

PROMPT = """program.rs is a Verus program that does not verify yet. Make it verify. Check your work with
`verus program.rs` as often as you like; it is done when Verus reports 0 errors.

Rules (matching the {pipeline} repair pipeline's own code-change check):
- Do not change executable code, requires/ensures clauses, or decreases clauses on functions.
- {spec_rule}
- Do not add assume, admit, #[verifier::external_body] or #[verifier::admit].
- You may add or change loop invariants, loop decreases, assertions, proof blocks, and proof
  functions/lemmas.
- You may fix or remove a `use` line that does not resolve.

If you become convinced the contract is false, so no proof can exist without changing it, stop
and write UNPROVABLE.md giving a concrete input on which the code violates the contract."""


SPEC_RULE = {
    "autoverus": "You may rewrite a spec function's body if it does not compile, but keep its intended meaning.",
    "verusage": "Do not change spec functions.",
}


def prompt(pipeline: str) -> str:
    return PROMPT.format(pipeline={"autoverus": "AutoVerus", "verusage": "VeruSAGE"}[pipeline],
                         spec_rule=SPEC_RULE[pipeline])


def sample(args: argparse.Namespace) -> None:
    """Draw failing test trees (default trajectory unverified), one per task."""
    with (HERE / "test_trees.csv").open() as stream:
        rows = [r for r in csv.DictReader(stream) if r["default_verified"] == "False"]
    rng, picked, tasks = random.Random(args.seed), [], set()
    for row in rng.sample(rows, len(rows)):
        if row["task_id"] not in tasks:
            picked.append(row)
            tasks.add(row["task_id"])
        if len(picked) == args.n:
            break
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(picked[0]))
        writer.writeheader()
        writer.writerows(picked)
    print(f"{len(picked)} trees from {len(rows)} failing test trees -> {args.out}")


def token() -> str:
    """The subscription access token, read at run time and passed only through the environment."""
    creds = json.loads((Path.home() / ".claude/.credentials.json").read_text())
    return creds["claudeAiOauth"]["accessToken"]


def repair(row: dict, model: str, out: Path, timeout: int) -> None:
    """Models named claude-* run through claude_agent.py (Agent SDK); others through opencode."""
    work = out / row["root"]
    if (work / "agent.json").exists():
        return
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "roots" / f"{row['root']}.rs", work / "program.rs")
    start = time.time()
    mount = ["-v", f"{work.resolve()}:/work:Z", "-w", "/work"]
    if model.startswith("claude-"):
        proc = subprocess.run(
            ["podman", "run", "--rm", "-i", "-e", "CLAUDE_CODE_OAUTH_TOKEN", "-e", "IS_SANDBOX=1", *mount,
             "-v", f"{HERE}:/steer:ro,z", IMAGE, "timeout", str(timeout),
             "python", "/steer/claude_agent.py", model, "100"],
            input=prompt(row["pipeline"]), capture_output=True, text=True, env=os.environ | {"CLAUDE_CODE_OAUTH_TOKEN": token()})
    else:
        with (work / "transcript.jsonl").open("w") as log:
            proc = subprocess.run(
                ["podman", "run", "--rm", *mount, IMAGE, "timeout", str(timeout),
                 "opencode", "run", "--auto", "--format", "json", "-m", model, prompt(row["pipeline"])],
                stdout=log, stderr=subprocess.PIPE, text=True)
    (work / "agent.json").write_text(json.dumps({
        "tree_id": row["tree_id"], "model": model, "exit": proc.returncode,
        "seconds": round(time.time() - start), "stderr": proc.stderr[-2000:]}))
    print(f"{row['task_id']}: exit {proc.returncode} after {time.time() - start:.0f}s", flush=True)


def run(args: argparse.Namespace) -> None:
    with args.sample.open() as stream:
        rows = list(csv.DictReader(stream))
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.sample, args.out / "sample.csv")
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(lambda r: repair(r, args.model, args.out, args.timeout), rows))


def verus(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(["podman", "run", "--rm", "-v", f"{path.parent.resolve()}:/work:Z", "-w", "/work",
                           IMAGE, "timeout", "300", "verus", path.name], capture_output=True, text=True)
    summary = re.findall(r"verification results:: (\d+) verified, (\d+) errors", proc.stdout + proc.stderr)
    ok = proc.returncode == 0 and bool(summary) and summary[-1][1] == "0"
    return ok, summary[-1] if summary else "no summary"


def unchanged(original: Path, changed: Path, *flags: str, drop_use: bool = False, gate: str = "autoverus") -> bool:
    """The pipeline's own code-change check: `lynette compare -t` for AutoVerus, `lynette additions`
    for VeruSAGE. drop_use ignores `use` lines and trigger annotations on both sides."""
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for name, path in (("a.rs", original), ("b.rs", changed)):
            lines = path.read_text().splitlines()
            if drop_use:
                lines = [re.sub(r"#!\[trigger(?:[^\[\]]|\[[^\]]*\])*\]|#\[trigger\]", "",
                                re.sub(r"#\[trigger\]\s*\(([^()]*)\)", r"\1", l))
                         for l in lines if not l.lstrip().startswith("use ")]
            (Path(tmp) / name).write_text("\n".join(lines) + "\n")
            files.append(str(Path(tmp) / name))
        command = ["compare", "-t", *flags] if gate == "autoverus" else ["additions"]
        return subprocess.run([str(LYNETTE), *command, *files], capture_output=True).returncode == 0


def usage(work: Path) -> dict:
    """Tokens, cost and tool calls from an opencode or Agent SDK transcript, or pipeline proxy calls."""
    tokens, cost, tools = 0, 0.0, 0
    if not (work / "transcript.jsonl").exists():
        lines = (work / "usage.jsonl").read_text().splitlines() if (work / "usage.jsonl").exists() else []
        for line in lines:
            call = json.loads(line)
            u = call["usage"]
            tokens += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + \
                u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
            cost += call.get("total_cost_usd") or 0
        return {"tokens": tokens, "cost": round(cost, 4), "tool_calls": 0, "model_calls": len(lines)}
    for line in (work / "transcript.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("kind") == "ResultMessage":
            u = event.get("usage") or {}
            tokens += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + \
                u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0)
            cost += event.get("total_cost_usd") or 0
        if event.get("kind") == "AssistantMessage":
            tools += sum(isinstance(b, dict) and "input" in b and "name" in b for b in event.get("content", []))
        part = event.get("part", {})
        if event.get("type") == "step_finish":
            t = part.get("tokens", {})
            tokens += t.get("input", 0) + t.get("output", 0) + t.get("reasoning", 0)
            cost += part.get("cost", 0) or 0
        if event.get("type") == "tool_use":
            tools += 1
    return {"tokens": tokens, "cost": round(cost, 4), "tool_calls": tools}


def grade(args: argparse.Namespace) -> None:
    with (args.out / "sample.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    results = []
    for row in rows:
        work = args.out / row["root"]
        if not (work / "agent.json").exists():
            continue
        original, program = HERE / "roots" / f"{row['root']}.rs", work / "program.rs"
        ok, summary = verus(program)
        text, base = program.read_text(), original.read_text()
        result = {
            "task_id": row["task_id"], "pipeline": row["pipeline"], "gen_model": row["gen_model"],
            "root_types": row["root_types"], "default_verified": row["default_verified"],
            "steer_verified": row["steer_verified"], "verified": ok, "summary": summary,
            "code_and_contract_unchanged": unchanged(original, program, gate=row["pipeline"]),
            "unchanged_modulo_imports_triggers": unchanged(original, program, drop_use=True, gate=row["pipeline"]),
            "spec_fns_unchanged": unchanged(original, program, "--spec"),
            "no_bypass_added": all(text.count(f) <= base.count(f) for f in FORBIDDEN),
            "claimed_unprovable": (work / "UNPROVABLE.md").exists(),
            **json.loads((work / "agent.json").read_text()) | usage(work),
        }
        result.pop("stderr")
        result["accepted"] = ok and result["code_and_contract_unchanged"] and result["no_bypass_added"]
        result["accepted_import_fix"] = ok and result["unchanged_modulo_imports_triggers"] and result["no_bypass_added"]
        results.append(result)
        print(json.dumps(result), flush=True)
    (args.out / "grades.json").write_text(json.dumps(results, indent=1))
    accepted = sum(r["accepted"] for r in results)
    print(f"\naccepted {accepted}/{len(results)} "
          f"({sum(r['accepted_import_fix'] for r in results)} ignoring imports and triggers); recorded pipeline default verified "
          f"{sum(r['default_verified'] == 'True' for r in results)}, VeruSteer "
          f"{sum(r['steer_verified'] == 'True' for r in results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("sample", type=Path)
    p.add_argument("--model", default="opencode/deepseek-v4.1-flash-free")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--timeout", type=int, default=1200)
    p = sub.add_parser("grade")
    p.add_argument("out", type=Path)
    args = parser.parse_args()
    {"sample": sample, "run": run, "grade": grade}[args.command](args)


if __name__ == "__main__":
    main()
