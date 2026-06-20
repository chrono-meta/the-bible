#!/usr/bin/env python3
"""
The Bible — gate_cli: a stdin->stdout JSON bridge over the per-turn gate.

Makes the mechanical grounding gate callable as an EXTERNAL TOOL by any agent runtime
(a subprocess, an MCP tool wrapper, a shell pipe). The agent emits one candidate turn as
JSON on stdin; this script runs it through gate_runtime.run_turn and writes the verdict
JSON on stdout. Stdlib only.

INPUT  (one JSON object on stdin):
  {
    "user_input":       "<the user's message>",        (str, required)
    "candidate_output": "<assistant reply to gate>",    (str, required)
    "citations":        [["<quote>", "<ref>"], ...],    (list of [quote, ref], optional)
    "engine":           "auto" | "l1" | "v3"            (optional; default "auto")
  }

OUTPUT (one JSON object on stdout):
  { "verdict": "...", "output": "...", "engine": "...", "blocked": <bool>, ... }
  On bad input -> {"verdict": "ERROR", "error": "...", "blocked": true} and exit code 2.

EXIT CODES:
  0  PASS   (candidate may be surfaced unchanged)
  1  blocked by the gate (a non-PASS verdict — surface result["output"] instead)
  2  input/usage error
"""
import json
import sys

# import the wrapper (which imports the real gate engines)
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_runtime import run_turn  # noqa: E402


def _normalize_citations(raw):
    """Accept [[quote, ref], ...] or [{"quote":...,"ref":...}, ...] -> list of (quote, ref)."""
    if raw is None:
        return []
    out = []
    for item in raw:
        if isinstance(item, dict):
            out.append((item.get("quote", ""), item.get("ref", "")))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append((item[0], item[1]))
        else:
            raise ValueError("each citation must be [quote, ref] or {quote, ref}")
    return out


def main(argv=None):
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        json.dump({"verdict": "ERROR", "error": "invalid JSON on stdin: %s" % e,
                   "blocked": True}, sys.stdout)
        sys.stdout.write("\n")
        return 2

    if not isinstance(payload, dict):
        json.dump({"verdict": "ERROR", "error": "stdin JSON must be an object",
                   "blocked": True}, sys.stdout)
        sys.stdout.write("\n")
        return 2

    try:
        user_input = payload.get("user_input", "")
        candidate_output = payload.get("candidate_output", "")
        citations = _normalize_citations(payload.get("citations"))
        engine = payload.get("engine", "auto")
    except ValueError as e:
        json.dump({"verdict": "ERROR", "error": str(e), "blocked": True}, sys.stdout)
        sys.stdout.write("\n")
        return 2

    result = run_turn(user_input, candidate_output, citations, engine=engine)
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# OPTIONAL MCP server sketch (NOT executed; requires the `mcp` package).
# Uncomment + `pip install mcp` to expose the gate as an MCP tool. This is a
# clearly-marked stub — the stdlib CLI above is the primary, must-work bridge.
# ---------------------------------------------------------------------------
# def _mcp_server():  # pragma: no cover
#     """Requires the `mcp` package (`pip install mcp`). Not part of the stdlib path."""
#     from mcp.server.fastmcp import FastMCP  # type: ignore
#     server = FastMCP("the-bible-gate")
#
#     @server.tool()
#     def gate_turn(user_input: str, candidate_output: str,
#                   citations: list | None = None, engine: str = "auto") -> dict:
#         """Run one chat turn through the mechanical scripture-grounding safety gate."""
#         cites = _normalize_citations(citations)
#         return run_turn(user_input, candidate_output, cites, engine=engine)
#
#     server.run()  # stdio transport
#
# # To launch: uncomment and call _mcp_server() (e.g. behind a `--mcp` flag).
