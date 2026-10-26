"""Blind spec review: does a cheap model catch the real problems from the code alone?

Claude Haiku 5.5 sees each verified program (no reference, no evaluator flags)
and lists postconditions that fail to pin down the code's behavior and
preconditions that reject inputs the code handles. Run inside the VerusEval
container from the release root, with CLAUDE_CODE_OAUTH_TOKEN or an API key set.

    python haiku/review_specs.py runs/regrade-30 > results/regrade-30/haiku_review.jsonl
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import re
import sys

PROMPT = """Below is a Rust function with a Verus contract (requires/ensures) and proof. Verus has
already verified it. Review only the contract against what the code actually does; ignore
loop invariants, asserts and proof blocks.

Report two kinds of problems:
- weak_post: behavior of the code that the ensures clauses do not pin down, so a wrong
  implementation could still satisfy the contract.
- extra_pre: requires clauses that reject inputs the code would handle correctly.

```rust
{code}
```

Reply with only JSON: {{"weak_post": ["..."], "extra_pre": ["..."]}} (empty lists if none)."""


async def ask(code: str) -> tuple[str, float]:
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
    options = ClaudeAgentOptions(model="claude-haiku-5-5", system_prompt="You are a careful formal-methods reviewer.",
                                 tools=[], max_turns=1, setting_sources=[])
    result = None
    async for message in query(prompt=PROMPT.format(code=code), options=options):
        if isinstance(message, ResultMessage):
            result = message
    return result.result, result.total_cost_usd


def review(row: dict) -> dict:
    reply, cost = asyncio.run(ask(Path(row["generated_path"]).read_text()))
    found = re.search(r"\{.*\}", reply, re.S)
    try:
        parsed = json.loads(found.group(0)) if found else {"raw": reply[:500]}
    except json.JSONDecodeError:
        parsed = {"raw": reply[:500]}
    return {"task_id": row["task_id"], "model": row["model"], **parsed, "cost": cost}


def main() -> None:
    with (Path(sys.argv[1]) / "programs.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    with ThreadPoolExecutor(5) as pool:
        for result in pool.map(review, rows):
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
