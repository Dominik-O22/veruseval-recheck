"""OpenAI-compatible /v1/chat/completions endpoint backed by the Claude Agent SDK.

Lets the AutoVerus/VeruSAGE repair pipelines run unmodified against a Claude model: point
LLM_BASE_URL at http://127.0.0.1:<port>/v1. Every request is answered by PROXY_MODEL whatever model
name the pipeline sends. Each completion is a one-turn call with no tools and no settings; earlier
turns (few-shot examples) are inlined, as in the StarVerus adapter. temperature, max_tokens and
response_format are not forwarded. Usage goes to PROXY_USAGE_LOG as JSON lines.

    PROXY_MODEL=claude-haiku-5-5 PROXY_USAGE_LOG=usage.jsonl python sdk_proxy.py 8765
"""
from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sys
import time

MODEL = os.environ.get("PROXY_MODEL", "claude-haiku-5-5")


def text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or [])


def complete(messages: list[dict]) -> str:
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

    system = "\n\n".join(text(m["content"]) for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    earlier = "".join(
        f"<{'example_input' if m['role'] == 'user' else 'example_output'}>\n{text(m['content'])}\n"
        f"</{'example_input' if m['role'] == 'user' else 'example_output'}>\n\n"
        for m in turns[:-1])
    user = (f"Worked examples:\n\n{earlier}Now the actual task:\n\n" if earlier else "") + text(turns[-1]["content"])
    options = ClaudeAgentOptions(model=MODEL, system_prompt=system, tools=[], max_turns=1, setting_sources=[])

    async def once() -> str:
        result = None
        async for message in query(prompt=user, options=options):  # drain fully
            if isinstance(message, ResultMessage):
                result = message
        if result is None or result.is_error or result.result is None:
            raise RuntimeError(f"Agent SDK call failed: {result and result.subtype}")
        if log := os.environ.get("PROXY_USAGE_LOG"):
            with open(log, "a") as stream:
                stream.write(json.dumps({"usage": result.usage, "total_cost_usd": result.total_cost_usd}) + "\n")
        return result.result

    for attempt in range(4):
        try:
            return asyncio.run(once())
        except Exception as error:  # retry transient SDK failures
            print(f"proxy: attempt {attempt + 1} failed: {error}", file=sys.stderr, flush=True)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError("Agent SDK call failed after retries")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        try:
            choices = [{"index": i, "finish_reason": "stop",
                        "message": {"role": "assistant", "content": complete(body["messages"])}}
                       for i in range(body.get("n") or 1)]
            payload, status = {"id": f"proxy-{time.time_ns()}", "object": "chat.completion",
                               "created": int(time.time()), "model": body.get("model", MODEL),
                               "choices": choices, "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                                                             "total_tokens": 0}}, 200
        except Exception as error:
            payload, status = {"error": {"message": str(error), "type": "server_error"}}, 500
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
