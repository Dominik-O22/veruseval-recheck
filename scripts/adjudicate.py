"""Second opinion on the evaluator's "invalid" contract comparisons.

The evaluator records an implication as invalid whenever Verus reports
"postcondition not satisfied", which only means Verus could not prove it
unaided within 20 seconds. For each such check this script captures the exact
harness the evaluator verified and tries, cheapest first:

  1. tactics, no LLM: a larger rlimit, then extra fuel for recursive spec fns;
  2. models via the Agent SDK, escalating haiku -> sonnet -> opus, each with
     Verus error feedback between attempts.

Proof text is spliced into the unchanged lemma (plus optional helper lemmas)
and the whole file is re-verified, so a "proved" verdict is checked by Verus
alone. Counterexamples are model claims, accepted only from the last model.

By default only the reliability directions are checked (reference precondition
=> generated, generated postcondition => reference); failures in the other two
mean the generated contract is more general or stronger, which verdicts.py
treats as safe.

    python haiku/adjudicate.py runs/haiku-fair20 [--label haiku-5-5] [--task ID] [--all-directions]

Writes <run>/adjudication.json and appends LLM usage to <run>/adjudication_usage.jsonl.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import metrics_rebuild.share.lemma_implication as li
import metrics_rebuild.share.semantic_strength as ss
from metrics_rebuild.metrics.proportion_at_least_gt import _strength_classification

DIRECTION = {
    "ground_pre_implies_gen_pre": "pre_ref_to_gen",
    "gen_post_implies_ground_post": "post_gen_to_ref",
    "gen_pre_implies_ground_pre": "pre_gen_to_ref",
    "ground_post_implies_gen_post": "post_ref_to_gen",
}
RELIABILITY = {"pre_ref_to_gen", "post_gen_to_ref"}
# Proof text containing any of these could prove anything, so it is rejected.
FORBIDDEN = ("assume", "admit", "external_body", "external_fn", "#[verifier", "axiom", "uninterp", "unsafe")
LADDER = (("claude-haiku-5-5", 2), ("claude-sonnet-5-5", 2), ("claude-opus-5-5", 4))
RLIMIT = "100"

PROMPT = """You are checking a Verus lemma that an automated evaluator could not verify.
Verus failed with "postcondition not satisfied", which may mean the implication is
false, or only that the SMT solver needed help (induction, nonlinear_arith,
bit_vector, sequence extensionality, unfolding recursive spec fns, etc.).

Here is the full harness. The lemma to prove is `{lemma}` at the end; its body is empty.

```rust
{harness}
```
{feedback}
If the lemma is provable, reply with exactly two fenced blocks:
```rust helpers
// zero or more new proof fns (recursive lemmas etc.); may be empty
```
```rust body
// statements that go inside the braces of {lemma}
```
You may not change the lemma statement or any existing item, and you may not use
assume, admit, external_body or any #[verifier] attribute.

If you are confident the implication is false, reply instead with a single line
starting with COUNTEREXAMPLE: followed by concrete argument values and why it fails."""


def capture_checks(generated: Path, reference: Path, directions: set[str]) -> list[dict]:
    """Run the evaluator's own strength comparison, recording each harness and outcome."""
    records: list[dict] = []
    label: dict = {}
    original_run, original_check = subprocess.run, ss._lemma_check

    def run(command, *args, **kwargs):
        result = original_run(command, *args, **kwargs)
        target = next((Path(c) for c in command if str(c).endswith(".rs")), None)
        if target and "--no-verify" not in command and "sqm_lemma_" in str(target):
            records.append({**label, "harness": target.read_text(), "lemma": target.stem})
        return result

    def check(**kwargs):
        label.update(check=kwargs["check_name"], function=kwargs["function_name"])
        result = original_check(**kwargs)
        if records and records[-1].get("check") == kwargs["check_name"]:
            records[-1]["status"] = result.get("status")
        return result

    li.subprocess.run, ss._lemma_check = run, check
    try:
        _strength_classification(str(generated), str(reference))
    finally:
        li.subprocess.run, ss._lemma_check = original_run, original_check
    return [r for r in records if r.get("check") in DIRECTION and DIRECTION[r["check"]] in directions]


def splice(harness: str, lemma: str, helpers: str, body: str) -> str:
    """Insert helpers before the lemma and the body inside its (empty) braces."""
    start = harness.index(f"proof fn {lemma}")
    open_brace = harness.index("{", harness.index("ensures", start) if "ensures" in harness[start:] else start)
    close_brace = harness.index("}", open_brace)
    if harness[open_brace + 1:close_brace].strip():
        raise ValueError("lemma body is not empty")
    return (harness[:start] + helpers.strip() + "\n\n" + harness[start:open_brace + 1]
            + "\n" + body.strip() + "\n" + harness[close_brace:])


def verus(text: str) -> tuple[bool, str]:
    """Verify the whole file, so helper lemmas are checked too."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "adjudicate.rs"
        path.write_text(text)
        try:
            run = subprocess.run([os.environ.get("VERUS_PATH", "/opt/verus/verus"), "--rlimit", RLIMIT, str(path)],
                                 capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            return False, "verus timed out after 240s"
    out = run.stdout + run.stderr
    return run.returncode == 0 and "0 errors" in out, out[-3000:]


def tactics(harness: str) -> list[tuple[str, str]]:
    """Canned proof bodies tried before any model call."""
    recursive = re.findall(r"spec fn (\w+)[^{;]*?decreases", harness, re.S)
    found = [("rlimit", "")]
    if recursive:
        found.append(("fuel", "\n".join(f"reveal_with_fuel({name}, 3);" for name in dict.fromkeys(recursive))))
    return found


async def ask(model: str, prompt: str, log: Path, tag: dict) -> str:
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
    options = ClaudeAgentOptions(model=model, system_prompt="You are an expert in Verus proofs.",
                                 tools=[], max_turns=1, setting_sources=[], effort="high")
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or result.result is None:
        raise RuntimeError(f"Agent SDK call failed: {result and result.errors}")
    with log.open("a") as stream:
        stream.write(json.dumps({**tag, "model": model, "usage": result.usage,
                                 "total_cost_usd": result.total_cost_usd}) + "\n")
    return result.result


def adjudicate(record: dict, log: Path, tag: dict) -> dict:
    for name, body in tactics(record["harness"]):
        if verus(splice(record["harness"], record["lemma"], "", body))[0]:
            return {"verdict": "proved", "by": f"tactic:{name}", "calls": 0}
    # Feedback carries across escalation, so a stronger model starts from the
    # weaker model's last failed attempt and its Verus errors.
    calls, claims, feedback = 0, [], ""
    for index, (model, attempts) in enumerate(LADDER):
        for _ in range(attempts):
            calls += 1
            reply = asyncio.run(ask(model, PROMPT.format(lemma=record["lemma"], harness=record["harness"],
                                                         feedback=feedback), log, tag))
            if reply.strip().startswith("COUNTEREXAMPLE:"):
                claims.append(f"{model}: {reply.strip()[:500]}")
                if index == len(LADDER) - 1:
                    return {"verdict": "claimed_counterexample", "by": model, "calls": calls, "detail": claims}
                break  # escalate rather than trust a cheaper model's refutation
            blocks = dict(re.findall(r"```rust (helpers|body)\n(.*?)```", reply, re.S))
            proof = blocks.get("helpers", "") + blocks.get("body", "")
            if "body" not in blocks:
                feedback = "\nYour previous reply did not contain a ```rust body block.\n"
                continue
            if any(word in proof for word in FORBIDDEN):
                feedback = "\nYour previous reply used a forbidden construct; prove it honestly.\n"
                continue
            ok, out = verus(splice(record["harness"], record["lemma"], blocks.get("helpers", ""), blocks["body"]))
            if ok:
                return {"verdict": "proved", "by": model, "calls": calls, "proof": proof}
            feedback = f"\nYour previous attempt:\n```rust\n{proof}\n```\nfailed with:\n```\n{out}\n```\n"
    return {"verdict": "unresolved", "calls": calls, "detail": claims}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--label", help="Only programs with this model label (default: all).")
    parser.add_argument("--task", action="append", help="Limit to these task IDs.")
    parser.add_argument("--all-directions", action="store_true")
    args = parser.parse_args()
    directions = set(DIRECTION.values()) if args.all_directions else RELIABILITY
    with (args.run / "programs.csv").open() as stream:
        programs = [r for r in csv.DictReader(stream) if (not args.label or r["model"] == args.label)
                    and (not args.task or r["task_id"] in args.task)]
    with (ROOT / "data/evaluation/target_functions.csv").open() as stream:
        references = {r["task_id"]: r["reference_path"] for r in csv.DictReader(stream)}
    log = args.run / "adjudication_usage.jsonl"
    results = []
    for program in programs:
        sample = "|".join(program[k] for k in ("workflow", "model", "shot", "task_id"))
        for record in capture_checks(Path(program["generated_path"]), ROOT / references[program["task_id"]], directions):
            direction = DIRECTION[record["check"]]
            if record.get("status") == "valid":
                outcome = {"verdict": "valid_on_recheck", "calls": 0}
            else:
                outcome = adjudicate(record, log, {"sample": sample, "direction": direction})
            results.append({"sample": sample, "task_id": program["task_id"], "model": program["model"],
                            "function": record["function"], "direction": direction, **outcome})
            print(f"{sample:<70}{record['function']:<22}{direction:<17}{outcome['verdict']}"
                  f" [{outcome.get('by', '-')}, {outcome['calls']} calls]", flush=True)
    (args.run / "adjudication.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
