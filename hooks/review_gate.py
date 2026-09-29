"""PreToolUse hook: no journal reaches Xero without a human approval on file.

Claude Code sends the pending tool call as JSON on stdin. If the journal id is not in
review/approved.json the call is denied before it runs, and the reason goes back to the agent.
"""
import json, sys, pathlib

call = json.load(sys.stdin)
jid = (call.get("tool_input") or {}).get("journal_id", "")
approved_file = pathlib.Path("review/approved.json")
approved = json.loads(approved_file.read_text(encoding="utf8")) if approved_file.exists() else []

if jid in approved:
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": f"Human review gate: {jid or 'this journal'} is not in review/approved.json. "
                                "Queue it with queue_review_item and stop."}}))
