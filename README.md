# Xero review agents

Three Claude Code agents review one month of an Australian client's Xero books for GST, coding and
bank reconciliation errors. They read Xero through an MCP server, write every finding to a review
queue, and cannot post anything to Xero until a person approves it. A scoring harness measures
whether their findings are right, not just whether they ran.

Built by Judah Rivera as a working sample for an application. **All data is invented** (Harbourline
Interiors Pty Ltd, August 2026). It has not been run against a live Xero file.

## What happens in a review

```
Xero (via MCP server)
   │  read only: organisation, accounts, contacts, bank transactions, bank statement
   ▼
Orchestrator (Claude Code) ── launches in parallel ──┬── gst-reviewer
                                                      ├── coding-reviewer
                                                      └── recon-reviewer
   │  each reads the firm's rules (SKILL.md), reads every line in its scope,
   │  and queues findings with evidence and a confidence
   ▼
review/queue.jsonl  ──►  a person reviews  ──►  review/approved.json  ──►  journal may post
                                   (a hook blocks any journal not approved)
```

## For a non-technical reader

- **The agents never change the books.** The only thing they can write is a line in the review queue.
  Posting a journal needs a person to approve it first, and that is enforced twice: by a hook that
  stops the call before it happens, and by the server itself.
- **Every call to Xero is logged** in `review/audit.jsonl`, so a reviewer can see exactly what an agent
  read before it made a claim.
- **The rules are the firm's, in one file.** `SKILL.md` holds the GST, coding and reconciliation rules.
  Change a rule there and all three agents follow it on the next run.
- **We know when an agent is wrong** because the demo month has 12 planted errors and 4 traps
  (things that look wrong but are correct). `evals/score.py` reports what was found, what was missed,
  and whether any trap was flagged. One good run proves nothing, so `evals/run_batch.py` runs the
  review several times and reports the spread.

## Files

| Path | What it is |
|---|---|
| `mcp_server/xero_server.py` | The `xero` MCP server (Python, official MCP SDK). Read tools plus `queue_review_item` and a guarded `post_manual_journal`. |
| `.mcp.json` | Tells Claude Code how to start the server. |
| `.claude/agents/*.md` | The three reviewer subagents, each limited to the tools it needs. |
| `.claude/skills/xero-month-review/SKILL.md` | The firm's review rules. |
| `.claude/settings.json` | Permissions and the two hooks. |
| `hooks/review_gate.py` | PreToolUse hook: denies any journal not in `review/approved.json`. |
| `hooks/audit_log.py` | PostToolUse hook: logs every Xero tool call. |
| `data/build_fixtures.py` | Builds the demo month in Xero's object shapes, plus the answer key. |
| `evals/score.py` | Precision, recall, traps, duplicates, and a hard fail if anything posted. |
| `evals/run_batch.py` | Runs the whole review N times and scores each run. |
| `tests/test_guards.py` | Tests for the gate, the server lock, the data and the scorer. |
| `runs/` | Real session logs, queues and scores from the runs described below. |

## Run it

```
pip install "mcp[cli]" pytest
python data/build_fixtures.py
python -m pytest -q
claude          # then: "Run the August 2026 month review"
python evals/score.py
python evals/run_batch.py 3
```

## What the runs showed

The scores in `runs/` are real. The history matters more than the best number:

1. **Run 1:** 10 of 11 planted errors found, no traps flagged, nothing posted. The miss was a bank fee
   coded with GST. The session log showed why: the subagents had no file-reading tool, so none of
   them could open `SKILL.md`, and the GST reviewer applied general GST rules instead of the firm's.
   The one extra finding (GST claimed on private groceries) was right and my answer key had missed
   it, so it was added to the key.
2. **Fix:** gave each subagent `Read`.
3. **Run 2:** the bank fee was caught, but the transposed amount was queued under the statement line id
   instead of the transaction id, and the groceries GST finding did not come back. Two changes: the
   rules now say which id to use and that private spending also carries a GST finding, and the scorer
   treats a statement line and its matched transaction as the same item.
4. **Batch of 3 after the fixes:** 12 of 12 found in every run, 100% precision, no traps flagged, nothing posted, about $0.93 of model usage per run. See `runs/03-batch-of-3-after-rule-fixes/`.

## Swapping in a live Xero file

Only `load()` in `mcp_server/xero_server.py` touches the data. For a live tenant it becomes calls to
the Xero Accounting API (OAuth 2.0 with a refresh token held in a vault, the tenant id, and paging on
BankTransactions), with the same tool names and return shapes, so the agents and rules do not change.
Xero's rate limits (60 calls a minute per tenant) mean the server should cache the month's
transactions once per run rather than let each agent page through them again.
