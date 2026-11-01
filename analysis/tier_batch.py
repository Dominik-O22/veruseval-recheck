"""Cheap tier: one-shot Claude Haiku 5.5 through the Message Batches API.

Each still-open lemma gets one request asking for a proof or a literal counterexample. Nothing the
model says is a verdict: `check` runs every answer through gate2_check, inside the container.

    run on the host, with ANTHROPIC_API_KEY set:
        python analysis/tier_batch.py submit open.jsonl HARNESS_DIR batch.json
        python analysis/tier_batch.py fetch batch.json answers.jsonl
    run in the container:
        python -I analysis/tier_batch.py check answers.jsonl HARNESS_DIR verdicts.jsonl

For gate 2d, `submit-inputs` asks for an input satisfying a guarded lemma's preconditions instead, and
`check-inputs` runs each through gate2_check.satisfy. `fetch` is the same.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

MODEL = os.environ.get("TIER_MODEL", "claude-haiku-5-5")
MAX_TOKENS = int(os.environ.get("TIER_MAX_TOKENS", "12000"))
PROMPT = """Below is a Verus file. It ends with a lemma `{lemma}` whose body is empty. Verus could not prove it unaided.

Decide whether the lemma is true, then give either a proof or a concrete counterexample.

```rust
{harness}
```

If the lemma is true, set verdict to "proof", put any new proof fns in helpers, and put the statements for inside the lemma's braces in body. Leave values empty.
Do not change the lemma or any existing item. Do not use assume, admit, external_body or any #[verifier] attribute.

If the lemma is false, set verdict to "counterexample" and give one entry in values for every parameter. Leave helpers and body empty.
Each value must be a Rust literal of the parameter's type, such as 5i32, vec![1u8, 2], &vec![1i32], Some(1usize), (1i8, 2i8) or 'a'. Use no variables, function calls or expressions. Parameters: {params}.{retry}"""

RETRY = """

An earlier attempt failed. Do not repeat it. Change approach if needed, including changing your verdict.

Earlier attempt:
{attempt}

Verus reported:
{log}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["proof", "counterexample"]},
        "helpers": {"type": "string"},
        "body": {"type": "string"},
        "values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                "required": ["name", "value"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "helpers", "body", "values"],
    "additionalProperties": False,
}


INPUT_PROMPT = """Below is a Verus file. It ends with a lemma `{lemma}`. Ignore its ensures clause and leave it unproved. We only need to know that its requires clause can be true.

```rust
{harness}
```

Give one concrete value for every parameter so that every line of the requires clause holds at once. Parameters: {params}.
Each value must be a Rust literal of the parameter's type, such as 5i32, vec![1u8, 2], &vec![1i32], &[1i32, 2], Some(1usize), (1i8, 2i8), 'a', or a struct or enum value. Write out every element: no `vec![x; n]`, variables, function calls or expressions.
If the lemma has type parameters, set each in types, such as T to u8. If a requires clause needs a recursive spec fn unfolded, list that spec fn in fuel with how many unfoldings it needs. Otherwise leave types and fuel empty."""

NAMED = {"type": "array", "items": {
    "type": "object",
    "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
    "required": ["name", "value"],
    "additionalProperties": False,
}}
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "values": NAMED,
        "types": NAMED,
        "fuel": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "unfoldings": {"type": "integer"}},
            "required": ["name", "unfoldings"],
            "additionalProperties": False,
        }},
    },
    "required": ["values", "types", "fuel"],
    "additionalProperties": False,
}


def send(jobs: list[tuple[dict, str]], schema: dict, out: Path) -> None:
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    requests, index = [], {}
    for i, (job, text) in enumerate(jobs):
        custom_id = f"c{i}"
        index[custom_id] = {"id": job["id"], "form": job["form"]}
        requests.append(Request(custom_id=custom_id, params=MessageCreateParamsNonStreaming(
            model=MODEL, max_tokens=MAX_TOKENS, messages=[{"role": "user", "content": text}],
            output_config={"format": {"type": "json_schema", "schema": schema}})))
    batch = anthropic.Anthropic().messages.batches.create(requests=requests)
    out.write_text(json.dumps({"batch": batch.id, "index": index}))
    print(batch.id, len(requests), "requests")


def submit(open_path: Path, harness_dir: Path, out: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gate2_check import lemma_signature

    jobs = []
    for line in open_path.read_text().splitlines():
        job = json.loads(line)
        harness = (harness_dir / job["id"] / f"{job['form']}.rs").read_text()
        lemma, params, *_ = lemma_signature(harness)
        retry = RETRY.format(attempt=json.dumps(job["attempt"]), log=job["log"]) if job.get("attempt") else ""
        jobs.append((job, PROMPT.format(lemma=lemma, harness=harness, retry=retry,
                                        params=", ".join(f"{n}: {t}" for n, t in params))))
    send(jobs, SCHEMA, out)


def submit_inputs(open_path: Path, harness_dir: Path, out: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gate2_check import lemma_signature

    jobs = []
    for line in open_path.read_text().splitlines():
        job = json.loads(line)
        harness = (harness_dir / job["id"] / f"{job['form']}.rs").read_text()
        lemma, params, *_ = lemma_signature(harness)
        jobs.append((job, INPUT_PROMPT.format(lemma=lemma, harness=harness,
                                              params=", ".join(f"{n}: {t}" for n, t in params))))
    send(jobs, INPUT_SCHEMA, out)


def fetch(batch_path: Path, out: Path) -> None:
    import anthropic

    state = json.loads(batch_path.read_text())
    client = anthropic.Anthropic()
    while True:
        batch = client.messages.batches.retrieve(state["batch"])
        if batch.processing_status == "ended":
            break
        print(batch.processing_status, batch.request_counts.processing, flush=True)
        time.sleep(60)
    usage = [0, 0]
    with out.open("w") as stream:
        for result in client.messages.batches.results(state["batch"]):
            job = state["index"][result.custom_id]
            row = {**job, "result": result.result.type}
            if result.result.type == "succeeded":
                message = result.result.message
                usage[0] += message.usage.input_tokens
                usage[1] += message.usage.output_tokens
                row["stop"] = message.stop_reason
                row["text"] = "".join(b.text for b in message.content if b.type == "text")
            stream.write(json.dumps(row) + "\n")
    print("input tokens", usage[0], "output tokens", usage[1])


def check(answers: Path, harness_dir: Path, out: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gate2_check import prove, refute

    def work(row: dict) -> dict:
        harness = (harness_dir / row["id"] / f"{row['form']}.rs").read_text()
        base = {k: row.get(k) for k in ("id", "form")}
        try:
            answer = json.loads(row.get("text", ""))
        except json.JSONDecodeError:
            return {**base, "outcome": "bad json", "stop": row.get("stop")}
        if answer.get("verdict") == "proof":
            proof = f"{answer.get('helpers', '')}\n// ---- body\n{answer.get('body', '')}"
            result = prove(harness, proof, "100")
        elif answer.get("verdict") == "counterexample":
            result = refute(harness, {v["name"]: v["value"] for v in answer.get("values", [])})
        else:
            return {**base, "outcome": "no verdict"}
        return {**base, "claim": answer["verdict"], "outcome": result.get("outcome"), "reason": result.get("reason"),
                "answer": answer, "log": (result.get("log") or result.get("reason") or "")[:1200]}

    rows = [json.loads(l) for l in answers.read_text().splitlines()]
    with out.open("w") as stream, ThreadPoolExecutor(7) as pool:
        for result in pool.map(work, rows):
            stream.write(json.dumps(result) + "\n")


def check_inputs(answers: Path, harness_dir: Path, out: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gate2_check import satisfy

    def work(row: dict) -> dict:
        harness = (harness_dir / row["id"] / f"{row['form']}.rs").read_text()
        base = {k: row.get(k) for k in ("id", "form")}
        try:
            answer = json.loads(row.get("text", ""))
        except json.JSONDecodeError:
            return {**base, "outcome": "bad json", "stop": row.get("stop")}
        witness = {v["name"]: v["value"] for v in answer["values"]}
        witness["_types"] = {v["name"]: v["value"] for v in answer["types"]}
        witness["_fuel"] = {v["name"]: v["unfoldings"] for v in answer["fuel"]}
        result = satisfy(harness, witness)
        return {**base, "outcome": result.get("outcome"), "vacuity": result.get("vacuity"), "answer": answer,
                "log": (result.get("log") or result.get("reason") or "")[:1200]}

    rows = [json.loads(l) for l in answers.read_text().splitlines()]
    with out.open("w") as stream, ThreadPoolExecutor(7) as pool:
        for result in pool.map(work, rows):
            stream.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    {"submit": lambda: submit(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])),
     "submit-inputs": lambda: submit_inputs(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])),
     "check-inputs": lambda: check_inputs(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])),
     "fetch": lambda: fetch(Path(sys.argv[2]), Path(sys.argv[3])),
     "check": lambda: check(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))}[sys.argv[1]]()
