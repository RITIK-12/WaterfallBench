"""WaterfallBench single-call harness: one model call per task, identical for every model.

The harness (not the model) reads the task: the problem statement, the answer schema, the servicer reports and the
governing documents. It converts the EDGAR HTML to plain text (table rows kept as `cell | cell | ...` lines), sends
everything in ONE request, parses the JSON object in the reply and writes it to /workspace/answer.json. The model gets
no tools, no code execution and no second turn, so models are compared on the model alone.

Input cap: --max-input-tokens (default 1,000,000, estimated as characters / 3.5). Documents are packed reports
first, then the prospectus, then the closing agreements; if the cap is reached, the lowest-priority documents are
cut and the cut is recorded in usage.json.

Usage (inside the sandbox):
  python3 direct.py --problem /tmp/problem_statement.txt --task-id ID --model anthropic/claude-opus-5-5
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

WORKSPACE = Path(os.environ.get("WFB_WORKSPACE", "/workspace"))   # override only for local dry runs
OUT = Path(os.environ.get("WFB_DIRECT_OUT", "/tmp/waterfallbench-direct"))
CHARS_PER_TOKEN = 3.5

SYSTEM = (
    "You are an expert in asset-backed securities. You compute a trust's monthly distribution - the priority of "
    "payments (waterfall) - exactly as its trustee would, from the governing documents and the servicer reports "
    "you are given. Apply the documents' definitions, rates, day counts, targets and rounding. Reply with one JSON "
    "object only, no prose and no code fences."
)

# Published list prices, USD per million tokens (input, output), for the usage estimate only.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-fable-5-2": (8.00, 40.00),
    "claude-haiku-5-5": (0.50, 2.50),  # prompts over 100K tokens
    "kimi-k3p1-pro": (2.00, 10.00), "minimax-m3p1-flash": (0.15, 0.60),  # Fireworks serverless, standard tier
}


class _Text(HTMLParser):
    """EDGAR HTML -> text. Table rows become `a | b | c` lines; '$', '%', ')' glue cells join their number."""

    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table", "section", "title", "hr", "center"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.depth = 0          # nested table cells
        self.cell: list[str] = []
        self.row: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "tr" and self.depth == 0:
            self.row = []
        elif tag in ("td", "th"):
            if self.depth == 0:
                self.cell = []
            self.depth += 1
        elif tag == "br":
            (self.cell if self.depth else self.out).append(" " if self.depth else "\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th"):
            self.depth = max(0, self.depth - 1)
            if self.depth == 0:
                t = " ".join("".join(self.cell).split())
                if t:
                    self.row.append(t)
        elif tag == "tr" and self.depth == 0:
            cells: list[str] = []
            for c in self.row:
                if cells and c in ("%", ")", "%)"):
                    cells[-1] += c
                elif cells and cells[-1] in ("$", "(", "$("):
                    cells[-1] = (cells[-1] + c) if cells[-1] != "$" else "$" + c
                else:
                    cells.append(c)
            if cells:
                self.out.append("\n" + " | ".join(cells) + "\n")
            self.row = []
        elif tag in self.BLOCK and self.depth == 0:
            self.out.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        (self.cell if self.depth else self.out).append(data)


def html_to_text(src: str) -> str:
    p = _Text()
    p.feed(src)
    p.close()
    lines = [" ".join(line.split()) for line in "".join(p.out).splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def documents() -> list[tuple[str, str, int]]:
    """(label, text, priority) in packing order: reports (chronological), prospectus, closing agreements."""
    docs = []
    for f in sorted((WORKSPACE / "reports").glob("*.html")):
        docs.append((f"reports/{f.name}", html_to_text(f.read_text(encoding="utf-8", errors="replace")), 0))
    for f in sorted((WORKSPACE / "docs").glob("*.html"), key=lambda p: (not p.name.startswith("prospectus"), p.name)):
        docs.append((f"docs/{f.name}", html_to_text(f.read_text(encoding="utf-8", errors="replace")),
                     1 if f.name.startswith("prospectus") else 2))
    return docs


def build_prompt(problem: str, schema: str, max_input_tokens: int) -> tuple[str, str, dict]:
    budget = int(max_input_tokens * CHARS_PER_TOKEN) - len(SYSTEM) - len(problem) - len(schema) - 4000
    packed, info = [], {"documents": [], "truncated": []}
    for label, text, _prio in documents():
        block = f"===== FILE: {label} =====\n{text}\n"
        if len(block) <= budget:
            packed.append(block)
            budget -= len(block)
            info["documents"].append({"file": label, "chars": len(text)})
        elif budget > 2000:
            packed.append(block[:budget] + "\n[... truncated at the input cap ...]\n")
            info["documents"].append({"file": label, "chars": len(text), "kept_chars": budget})
            info["truncated"].append(label)
            budget = 0
        else:
            info["truncated"].append(label)
    docs_text = "# Documents\n\n" + "\n".join(packed)
    task_text = (
        "# Task\n\n" + problem.strip() + "\n\n# Answer schema (/workspace/answer_schema.json)\n\n" + schema.strip() +
        "\n\n# Reply format\n\nReply with ONLY the JSON object that belongs in /workspace/answer.json: every required "
        "field, exactly matching the schema (money as integer US cents)."
    )
    return docs_text, task_text, info


def parse_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object in the reply")
    return json.loads(t[a:b + 1])


def _save_reply(text: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "response.txt").write_text(text, encoding="utf-8")


def call_anthropic(model: str, docs_text: str, task_text: str, effort: str, max_out: int) -> tuple[str, dict]:
    import anthropic
    client = anthropic.Anthropic(timeout=3000.0, max_retries=2)
    kwargs = {}
    if effort:
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    with client.messages.stream(
        model=model, max_tokens=max_out, system=SYSTEM,
        messages=[{"role": "user", "content": [{"type": "text", "text": docs_text}, {"type": "text", "text": task_text}]}],
        **kwargs,
    ) as stream:
        msg = stream.get_final_message()
    text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
    _save_reply(text)                      # save the paid reply before anything else can fail
    u = getattr(msg, "usage", None)
    return text, {"stop_reason": getattr(msg, "stop_reason", None),
                  "input_tokens": getattr(u, "input_tokens", None), "output_tokens": getattr(u, "output_tokens", None),
                  "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None),
                  "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
                  "message_id": getattr(msg, "id", None)}


def call_openai(model: str, docs_text: str, task_text: str, effort: str, max_out: int) -> tuple[str, dict]:
    from openai import OpenAI
    client = OpenAI(timeout=3000.0, max_retries=2)
    kwargs = {"reasoning": {"effort": effort}} if effort else {}
    resp = client.responses.create(model=model, instructions=SYSTEM, input=docs_text + "\n\n" + task_text,
                                   max_output_tokens=max_out, **kwargs)
    text = getattr(resp, "output_text", "") or ""
    _save_reply(text)
    u = getattr(resp, "usage", None)
    return text, {"stop_reason": getattr(resp, "status", None), "input_tokens": getattr(u, "input_tokens", None),
                  "output_tokens": getattr(u, "output_tokens", None), "message_id": getattr(resp, "id", None)}


def call_fireworks(model: str, docs_text: str, task_text: str, effort: str, max_out: int) -> tuple[str, dict]:
    """Fireworks serverless (OpenAI-compatible chat API), streamed so long reasoning cannot hit an idle timeout."""
    from openai import OpenAI
    client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=os.environ["FIREWORKS_API_KEY"],
                    timeout=3000.0, max_retries=2)
    model_id = model if model.startswith("accounts/") else f"accounts/fireworks/models/{model}"
    kwargs = {"reasoning_effort": effort} if effort else {}
    stream = client.chat.completions.create(
        model=model_id, max_tokens=max_out, stream=True, stream_options={"include_usage": True},
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": docs_text + "\n\n" + task_text}],
        **kwargs)
    content, reasoning_chars, finish, usage, rid = [], 0, None, None, None
    for chunk in stream:
        rid = rid or getattr(chunk, "id", None)
        if getattr(chunk, "usage", None):
            usage = chunk.usage
        for ch in chunk.choices or []:
            d = ch.delta
            if d is not None and d.content:
                content.append(d.content)
            r = getattr(d, "reasoning_content", None) if d is not None else None
            if r:
                reasoning_chars += len(r)
            finish = ch.finish_reason or finish
    text = "".join(content)
    _save_reply(text)
    return text, {"stop_reason": finish, "input_tokens": getattr(usage, "prompt_tokens", None),
                  "output_tokens": getattr(usage, "completion_tokens", None), "reasoning_chars": reasoning_chars,
                  "message_id": rid}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--model", required=True, help="provider/model, e.g. anthropic/claude-opus-5-5 or openai/<model>")
    ap.add_argument("--max-input-tokens", type=int, default=1_000_000)
    ap.add_argument("--max-output-tokens", type=int, default=128_000)  # Fireworks caps at 131,072
    ap.add_argument("--effort", default="high", help="reasoning effort passed to the provider ('' = provider default)")
    ap.add_argument("--dry-run", action="store_true", help="build the prompt and write it to OUT/prompt.txt; no model call")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    provider, _, model = a.model.partition("/")
    problem = Path(a.problem).read_text(encoding="utf-8")
    schema = (WORKSPACE / "answer_schema.json").read_text(encoding="utf-8")
    docs_text, task_text, info = build_prompt(problem, schema, a.max_input_tokens)
    usage = {"task_id": a.task_id, "model": a.model, "effort": a.effort, "max_input_tokens": a.max_input_tokens,
             "prompt_chars": len(SYSTEM) + len(docs_text) + len(task_text), **info}
    if a.dry_run:
        OUT.joinpath("prompt.txt").write_text(SYSTEM + "\n\n" + docs_text + "\n\n" + task_text, encoding="utf-8")
        print(json.dumps({**usage, "est_input_tokens": int(usage["prompt_chars"] / CHARS_PER_TOKEN)}, indent=1)[:1500])
        return 0
    t0 = time.monotonic()
    status = 1
    try:
        if provider == "anthropic":
            text, meta = call_anthropic(model, docs_text, task_text, a.effort, a.max_output_tokens)
        elif provider == "openai":
            text, meta = call_openai(model, docs_text, task_text, a.effort, a.max_output_tokens)
        elif provider == "fireworks":
            text, meta = call_fireworks(model, docs_text, task_text, a.effort, a.max_output_tokens)
        else:
            raise SystemExit(f"unknown provider {provider!r}")
        usage.update(meta)
        (OUT / "response.txt").write_text(text, encoding="utf-8")
        answer = parse_json(text)
        (WORKSPACE / "answer.json").write_text(json.dumps(answer), encoding="utf-8")
        usage["answer_written"] = True
        status = 0
    except Exception as e:  # recorded; a missing answer scores 0 in the grader
        usage["error"] = f"{type(e).__name__}: {e}"[:2000]
        usage["answer_written"] = False
    finally:
        usage["seconds"] = round(time.monotonic() - t0, 1)
        p = PRICES.get(model)
        if p and usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            usage["est_cost_usd"] = round(usage["input_tokens"] / 1e6 * p[0] + usage["output_tokens"] / 1e6 * p[1], 4)
        (OUT / "usage.json").write_text(json.dumps(usage, indent=1), encoding="utf-8")
        print(json.dumps({k: usage.get(k) for k in ("task_id", "model", "input_tokens", "output_tokens", "est_cost_usd",
                                                     "seconds", "answer_written", "error", "truncated")}), flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
