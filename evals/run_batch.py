"""Runs the full multi-agent review N times from a clean queue and scores every run.

One good run proves nothing: agents vary run to run. This reports each run and the spread, so a
rule change is judged on the batch, not on the best run.

Run:  python evals/run_batch.py 3
Writes runs/batch-<n>/queue.jsonl, audit.jsonl, session.jsonl and summary.txt per run.
"""
import json, subprocess, sys, pathlib, shutil, re, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
PROMPT = ("Run the August 2026 month review for this Xero organisation. Launch the gst-reviewer, coding-reviewer "
          "and recon-reviewer subagents in parallel, one category each, as described in CLAUDE.md. When all three "
          "are done, read review/queue.jsonl and give me a short summary table: id, category, issue, proposed fix, "
          "confidence. Do not post anything to Xero.")
TOOLS = ("Task,Agent,Read,Glob,Grep,mcp__xero__get_organisation,mcp__xero__list_accounts,mcp__xero__list_contacts,"
         "mcp__xero__list_bank_transactions,mcp__xero__get_bank_statement,mcp__xero__get_account_totals,"
         "mcp__xero__queue_review_item")
stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
results = []
for i in range(1, N + 1):
    out = ROOT / "runs" / f"batch-{stamp}" / f"run-{i}"
    out.mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "review").glob("*.jsonl"):
        f.unlink()
    with open(out / "session.jsonl", "w", encoding="utf8") as s:
        subprocess.run(["claude", "-p", PROMPT, "--allowedTools", TOOLS, "--output-format", "stream-json", "--verbose"],
                       cwd=ROOT, stdout=s, stderr=subprocess.DEVNULL, shell=(sys.platform == "win32"))
    for f in ("queue.jsonl", "audit.jsonl"):
        if (ROOT / "review" / f).exists():
            shutil.copy(ROOT / "review" / f, out / f)
    score = subprocess.run([sys.executable, str(ROOT / "evals" / "score.py"), str(out / "queue.jsonl")],
                           capture_output=True, text=True).stdout
    (out / "score.txt").write_text(score, encoding="utf8")
    cost = [json.loads(l).get("total_cost_usd") for l in open(out / "session.jsonl", encoding="utf8")
            if '"type":"result"' in l.replace(" ", "")]
    rec = float(re.search(r"recall\s+(\d+)%", score).group(1))
    pre = float(re.search(r"precision\s+(\d+)%", score).group(1))
    results.append((i, rec, pre, "PASS" in score, cost[-1] if cost else None))
    print(f"run {i}: recall {rec:.0f}%  precision {pre:.0f}%  {'PASS' if results[-1][3] else 'FAIL'}  cost ${cost[-1] if cost else 0:.2f}",
          flush=True)

avg = lambda k: sum(r[k] for r in results) / len(results)
summary = (f"{N} runs  mean recall {avg(1):.0f}%  mean precision {avg(2):.0f}%  "
           f"passed {sum(r[3] for r in results)} of {N}  min recall {min(r[1] for r in results):.0f}%")
print(summary)
(ROOT / "runs" / f"batch-{stamp}" / "summary.txt").write_text(summary + "\n", encoding="utf8")
