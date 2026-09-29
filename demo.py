"""Live demo: tests, a full review run with Xero calls and findings streamed as they happen,
the score, then the review gate tested inside Claude Code.

Run in a console:  python demo.py
"""
import json, subprocess, sys, time, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parent
os.chdir(ROOT)
os.system("")  # enable ANSI colours on Windows consoles
C = {"dim": "\033[90m", "b": "\033[1m", "g": "\033[92m", "y": "\033[93m", "c": "\033[96m", "r": "\033[91m", "m": "\033[95m", "0": "\033[0m"}
TOOLS = ("Task,Agent,Read,Glob,Grep,mcp__xero__get_organisation,mcp__xero__list_accounts,mcp__xero__list_contacts,"
         "mcp__xero__list_bank_transactions,mcp__xero__get_bank_statement,mcp__xero__get_account_totals,"
         "mcp__xero__queue_review_item")
SHELL = sys.platform == "win32"


def say(t, col="0", pause=0.0):
    print(C[col] + t + C["0"], flush=True)
    time.sleep(pause)


def step(n, t):
    print(flush=True)
    say(f"── {n}  {t} " + "─" * max(0, 70 - len(t)), "c", 0.8)


say("Xero review agents · Harbourline Interiors (DEMO) · August 2026", "b")
say("3 Claude Code subagents · xero MCP server · review gate hook · scored against an answer key", "dim", 2)

step(1, "Tests: gate, server lock, data, scorer")
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines()[-2:]:
    say("   " + line, "g" if "passed" in line else "0")
time.sleep(1.5)

step(2, "Claude Code runs the month review (3 subagents in parallel)")
for f in pathlib.Path("review").glob("*.jsonl"):
    f.unlink()
prompt = ("Run the August 2026 month review for this Xero organisation. Launch the gst-reviewer, coding-reviewer and "
          "recon-reviewer subagents in parallel, one category each, as described in CLAUDE.md. When all three are done, "
          "read review/queue.jsonl and give me a short summary. Do not post anything to Xero.")
log = open("runs/demo-session.jsonl", "w", encoding="utf8")
p = subprocess.Popen(["claude", "-p", prompt, "--allowedTools", TOOLS, "--output-format", "stream-json", "--verbose"],
                     stdout=log, stderr=subprocess.DEVNULL, shell=SHELL)
seen_a, seen_q, t0 = 0, 0, time.time()
say("   claude -p \"Run the August 2026 month review...\"", "dim")
while True:
    a = pathlib.Path("review/audit.jsonl")
    q = pathlib.Path("review/queue.jsonl")
    if a.exists():
        rows = a.read_text(encoding="utf8").splitlines()
        for l in rows[seen_a:]:
            e = json.loads(l)
            tool = (e.get("tool") or "").replace("mcp__xero__", "")
            if tool == "queue_review_item":
                continue
            args = {k: v for k, v in (e.get("input") or {}).items() if v}
            say(f"   {C['dim']}{time.time() - t0:5.0f}s{C['0']}  xero.{tool}({', '.join(f'{k}={v}' for k, v in args.items())})", "0")
        seen_a = len(rows)
    if q.exists():
        rows = q.read_text(encoding="utf8").splitlines()
        for l in rows[seen_q:]:
            e = json.loads(l)
            col = {"gst": "y", "coding": "m", "recon": "c"}[e["category"]]
            say(f"   {C['dim']}{time.time() - t0:5.0f}s{C['0']}  {C[col]}QUEUED {e['id']:<8} {e['category']:<6}{C['0']} "
                f"{e['issue'][:92]}", "0")
        seen_q = len(rows)
    if p.poll() is not None:
        break
    time.sleep(0.4)
log.close()
cost = [json.loads(l).get("total_cost_usd") for l in open("runs/demo-session.jsonl", encoding="utf8") if '"type":"result"' in l]
say(f"   done in {time.time() - t0:.0f}s" + (f", ${cost[-1]:.2f} of model usage" if cost else ""), "g", 1.5)

step(3, "Score against the answer key (12 planted errors, 4 traps)")
r = subprocess.run([sys.executable, "evals/score.py"], capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    col = "g" if "PASS" in line else "r" if ("FAIL" in line or "MISSED" in line) else "y" if "EXTRA" in line else "0"
    say("   " + line, col, 0.15)
time.sleep(2)

step(4, "The gate: Claude Code is told to post a journal")
say("   claude -p \"Post manual journal MJ-0001 to Xero\"", "dim")
r = subprocess.run(["claude", "-p", "Call the xero post_manual_journal tool with journal_id MJ-0001, narration 'Reclass laptop "
                    "to 720', lines []. Report in one sentence exactly what happened.", "--allowedTools",
                    "mcp__xero__post_manual_journal"], capture_output=True, text=True, shell=SHELL)
say("   " + r.stdout.strip().replace("\n", " ")[:300], "0")
posted = pathlib.Path("review/posted.jsonl")
say(f"   review/posted.jsonl: {'MISSING, nothing posted' if not posted.exists() else posted.read_text()}", "g", 1)
say("   The hook denied it before the call ran. Approvals live in review/approved.json, edited by a person.", "g", 3)
