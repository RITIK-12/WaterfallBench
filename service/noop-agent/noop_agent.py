"""WaterfallBench-Pilot no-op agent: no model calls, standard library only."""

import argparse
import json
import os
from pathlib import Path
from typing import Any, cast

WORKSPACE = Path("/workspace")
OUTPUT_DIR = Path("/tmp/waterfallbench-noop")


def _object(value: object) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return cast("list[Any]", value) if isinstance(value, list) else []


def zero_from_schema(raw: object, root: object) -> Any:
    """A placeholder value for a JSON Schema: 0, "0", false, [], first enum value, ..."""
    schema = _object(raw)
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        target = _object(root)
        for part in ref[2:].split("/"):
            target = _object(target.get(part))
        return zero_from_schema(target, root)
    if "const" in schema:
        return schema["const"]
    if enum := _list(schema.get("enum")):
        return enum[0]
    for combinator in ("anyOf", "oneOf", "allOf"):
        if options := _list(schema.get(combinator)):
            return zero_from_schema(options[0], root)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in _list(cast(object, kind)) if k != "null"), "null")
    if kind == "object" or "properties" in schema:
        return {name: zero_from_schema(sub, root) for name, sub in _object(schema.get("properties")).items()}
    defaults: dict[str, Any] = {"array": [], "integer": 0, "number": 0, "string": "0", "boolean": False}
    return defaults.get(kind) if isinstance(kind, str) else None


def listing() -> str:
    lines: list[str] = []
    for path in sorted(WORKSPACE.rglob("*")):
        if path.is_file():
            lines.append(f"{path.stat().st_size:>12}  {path}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--mode", default="zeros", choices=["zeros", "empty", "missing", "malformed"])
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "workspace_listing.txt").write_text(listing())
    problem = args.problem.read_text(encoding="utf-8")
    print(f"[noop] task {args.task_id}: problem statement {len(problem)} chars, mode {args.mode}")

    answer_path = WORKSPACE / "answer.json"
    if args.mode == "zeros":
        schema = json.loads((WORKSPACE / "answer_schema.json").read_text(encoding="utf-8"))
        answer_path.write_text(json.dumps(zero_from_schema(schema, schema), indent=2) + "\n")
    elif args.mode == "empty":
        answer_path.write_text("{}\n")
    elif args.mode == "malformed":
        answer_path.write_text("{this is not json\n")
    if answer_path.exists():
        (OUTPUT_DIR / "answer.json").write_bytes(answer_path.read_bytes())
    print(f"[noop] wrote {answer_path if answer_path.exists() else 'no answer'}; cwd {os.getcwd()}")


if __name__ == "__main__":
    main()
