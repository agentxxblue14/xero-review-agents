"""PostToolUse hook: every Xero tool call is written to review/audit.jsonl with its inputs.

The reviewer can see exactly what each agent read before it made a claim.
"""
import json, sys, pathlib, datetime as dt

call = json.load(sys.stdin)
pathlib.Path("review").mkdir(exist_ok=True)
with open("review/audit.jsonl", "a", encoding="utf8") as f:
    f.write(json.dumps({"at": dt.datetime.now().isoformat(timespec="seconds"),
                        "tool": call.get("tool_name"), "input": call.get("tool_input")}) + "\n")
