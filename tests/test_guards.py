"""Tests for the parts that must never fail quietly: the review gate, the server's own lock,
the answer key's arithmetic, and the scorer. Run: python -m pytest -q
"""
import json, subprocess, sys, pathlib, asyncio, shutil
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp_server"))
import xero_server as xs  # noqa: E402


def run_hook(script, payload, cwd):
    r = subprocess.run([sys.executable, str(ROOT / "hooks" / script)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout


def test_gate_denies_unapproved_journal(tmp_path):
    code, out = run_hook("review_gate.py", {"tool_name": "mcp__xero__post_manual_journal",
                                            "tool_input": {"journal_id": "MJ-001"}}, tmp_path)
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "MJ-001" in decision["permissionDecisionReason"]


def test_gate_allows_approved_journal(tmp_path):
    (tmp_path / "review").mkdir()
    (tmp_path / "review" / "approved.json").write_text('["MJ-001"]')
    code, out = run_hook("review_gate.py", {"tool_name": "mcp__xero__post_manual_journal",
                                            "tool_input": {"journal_id": "MJ-001"}}, tmp_path)
    assert code == 0 and out.strip() == ""


def test_server_refuses_unapproved_journal_even_without_the_hook(monkeypatch, tmp_path):
    monkeypatch.setattr(xs, "REVIEW", tmp_path)
    res = xs.post_manual_journal("MJ-999", "test", [])
    assert res["ok"] is False
    assert not (tmp_path / "posted.jsonl").exists()


def test_queue_rejects_unknown_category(monkeypatch, tmp_path):
    monkeypatch.setattr(xs, "REVIEW", tmp_path)
    assert xs.queue_review_item("BT-0001", "vibes", "x", "y", "z", "high")["ok"] is False


def test_clean_gst_lines_are_one_eleventh():
    key = json.loads((ROOT / "evals" / "answer_key.json").read_text())
    planted = {p["id"] for p in key["planted"]}
    for t in xs.list_bank_transactions():
        li = t["LineItems"][0]
        if li["TaxType"] in ("INPUT", "OUTPUT") and t["BankTransactionID"] not in planted:
            assert abs(li["TaxAmount"] - round(t["Total"] / 11, 2)) < 0.005, t["BankTransactionID"]


def test_every_planted_id_exists():
    key = json.loads((ROOT / "evals" / "answer_key.json").read_text())
    ids = {t["BankTransactionID"] for t in xs.list_bank_transactions()} | {s["StatementLineID"] for s in xs.get_bank_statement()}
    for p in key["planted"] + key["must_not_flag"]:
        assert p["id"] in ids


def test_scorer_perfect_run_passes(tmp_path):
    key = json.loads((ROOT / "evals" / "answer_key.json").read_text())
    q = tmp_path / "queue.jsonl"
    q.write_text("\n".join(json.dumps({"id": p["id"], "category": p["category"]}) for p in key["planted"]))
    r = subprocess.run([sys.executable, str(ROOT / "evals" / "score.py"), str(q)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_scorer_fails_when_a_trap_is_flagged(tmp_path):
    key = json.loads((ROOT / "evals" / "answer_key.json").read_text())
    rows = [{"id": p["id"], "category": p["category"]} for p in key["planted"]]
    rows += [{"id": t["id"], "category": "gst"} for t in key["must_not_flag"]] * 1
    q = tmp_path / "queue.jsonl"
    q.write_text("\n".join(json.dumps(r) for r in rows))
    r = subprocess.run([sys.executable, str(ROOT / "evals" / "score.py"), str(q)], capture_output=True, text=True)
    assert "Traps flagged         4 of 4" in r.stdout
    assert r.returncode == 1
