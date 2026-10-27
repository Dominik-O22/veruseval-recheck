"""One Claude agent session repairing /work/program.rs, run inside the Verus container by run_agent.py.

Claude Code's preset system prompt, shell and file tools, no user settings. Every SDK message is
appended to /work/transcript.jsonl; the final line is the result with usage and cost.

    python claude_agent.py <model> <max_turns>   (prompt on stdin)
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import sys

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query


async def main(model: str, max_turns: int, prompt: str) -> None:
    options = ClaudeAgentOptions(
        model=model, cwd="/work", max_turns=max_turns, setting_sources=[],
        system_prompt={"type": "preset", "preset": "claude_code"},
        tools=["Bash", "Read", "Edit", "Write", "Glob", "Grep"], permission_mode="bypassPermissions")
    with open("/work/transcript.jsonl", "a") as log:
        async for message in query(prompt=prompt, options=options):
            record = dataclasses.asdict(message) if dataclasses.is_dataclass(message) else {"raw": str(message)}
            record["kind"] = type(message).__name__
            log.write(json.dumps(record, default=str) + "\n")
            log.flush()
            if isinstance(message, ResultMessage):
                print(f"result: {message.subtype}, turns {message.num_turns}, ${message.total_cost_usd}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.stdin.read()))
