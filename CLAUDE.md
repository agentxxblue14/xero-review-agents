# Xero review agents

Month-end bookkeeping review for Australian clients in Xero, run by Claude Code agents with a human
review gate. Invented demo data only (Harbourline Interiors Pty Ltd, August 2026).

## Layout

- `mcp_server/xero_server.py`: the `xero` MCP server. Reads are free; `queue_review_item` writes to the
  review queue only; `post_manual_journal` needs a human approval.
- `.claude/agents/`: `gst-reviewer`, `coding-reviewer`, `recon-reviewer`. Each owns one category.
- `.claude/skills/xero-month-review/SKILL.md`: the firm's review rules. Agents read it; they do not restate it.
- `hooks/`: `review_gate.py` (PreToolUse, blocks unapproved journals), `audit_log.py` (PostToolUse, logs every Xero call).
- `evals/score.py`: scores the review queue against `evals/answer_key.json`.

## Running a review

1. `python data/build_fixtures.py` (demo data) then clear `review/`.
2. Ask for the month review. Run the three reviewers in parallel as subagents, one category each.
3. When all three finish, check `review/queue.jsonl` has one row per finding and nothing in `review/posted.jsonl`.
4. `python evals/score.py` for precision and recall.

## Rules for this repo

- Never post to Xero from an agent. Approvals live in `review/approved.json`, edited by a person.
- A finding without evidence (the fields read) is not a finding.
- When a rule does not settle something, queue it as low confidence with the question for the client.
