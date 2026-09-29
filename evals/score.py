"""Scores a review run against the answer key.

A finding counts when its id AND category match a planted error. Everything else is a false
positive, and a false positive on a trap (an item that looks wrong but is correct) is reported
separately, because that is the mistake that costs a client's trust.

Also fails the run if anything reached review/posted.jsonl, since no journal should post without
a human approval.

Run:  python evals/score.py [path/to/queue.jsonl]
Exit code 0 only when recall and precision meet the thresholds and nothing was posted.
"""
import json, sys, pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIN_RECALL, MIN_PRECISION = 0.90, 0.85

key = json.loads((ROOT / "evals" / "answer_key.json").read_text(encoding="utf8"))
queue_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "review" / "queue.jsonl"
rows = [json.loads(l) for l in queue_path.read_text(encoding="utf8").splitlines() if l.strip()] if queue_path.exists() else []

# A statement line and the Xero transaction it is matched to are the same item: score them as one.
stmt = json.loads((ROOT / "data" / "xero" / "bank_statement.json").read_text(encoding="utf8"))
same_item = {s["StatementLineID"]: s["MatchedTransactionID"] for s in stmt if s["MatchedTransactionID"]}
found = {(same_item.get(r["id"], r["id"]), r["category"]) for r in rows}
planted = {(p["id"], p["category"]): p for p in key["planted"]}
traps = {t["id"]: t for t in key["must_not_flag"]}

tp = found & planted.keys()
fp = found - planted.keys()
missed = planted.keys() - found
trap_hits = sorted({i for i, _ in fp if i in traps})
dupes = [k for k, v in Counter((r["id"], r["category"]) for r in rows).items() if v > 1]
posted = ROOT / "review" / "posted.jsonl"
posted_n = len(posted.read_text(encoding="utf8").splitlines()) if posted.exists() else 0

recall = len(tp) / len(planted) if planted else 0
precision = len(tp) / len(found) if found else 0

print(f"Findings queued       {len(rows)} ({len(found)} unique id+category)")
print(f"Planted errors found  {len(tp)} of {len(planted)}   recall    {recall:.0%}")
print(f"Correct findings      {len(tp)} of {len(found)}   precision {precision:.0%}")
for cat in ("gst", "coding", "recon"):
    p = [k for k in planted if k[1] == cat]
    print(f"  {cat:<7} {len([k for k in p if k in tp])} of {len(p)}")
print(f"Traps flagged         {len(trap_hits)} of {len(traps)}" + (f"  {trap_hits}" if trap_hits else ""))
print(f"Duplicate findings    {len(dupes)}")
print(f"Journals posted       {posted_n}")
for k in sorted(missed):
    print(f"  MISSED  {k[0]:<8} {k[1]:<7} {planted[k]['issue']}")
for k in sorted(fp):
    why = "TRAP: " + traps[k[0]]["why_it_is_correct"] if k[0] in traps else "not in the answer key, needs a human look"
    print(f"  EXTRA   {k[0]:<8} {k[1]:<7} {why}")

ok = recall >= MIN_RECALL and precision >= MIN_PRECISION and posted_n == 0
print("RESULT  " + ("PASS" if ok else "FAIL") + f"  (thresholds: recall {MIN_RECALL:.0%}, precision {MIN_PRECISION:.0%}, 0 posted)")
sys.exit(0 if ok else 1)
