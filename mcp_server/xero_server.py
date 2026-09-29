"""MCP server that gives Claude read access to a Xero organisation, plus two guarded writes.

Reads come from data/xero/*.json, which mirror Xero API object shapes. To point this at a live
Xero tenant, replace `load()` with calls to the Xero Accounting API (BankTransactions, Invoices,
Accounts, Contacts, Reports/TrialBalance). The tool names and return shapes stay the same, so the
agents do not change.

Writes:
  queue_review_item   appends a finding to review/queue.jsonl. Nothing in Xero changes.
  post_manual_journal refuses unless the journal id is listed in review/approved.json, which only a
                      human edits. A PreToolUse hook blocks it too, so there are two locks, not one.

Run:  python mcp_server/xero_server.py   (stdio; Claude Code starts it from .mcp.json)
"""
import json, pathlib, datetime as dt
from collections import defaultdict
from mcp.server.mcpserver import MCPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "xero"
REVIEW = ROOT / "review"
REVIEW.mkdir(exist_ok=True)

server = MCPServer(name="xero", instructions=(
    "Read-only access to one Xero organisation for bookkeeping review. "
    "Record every finding with queue_review_item. Never call post_manual_journal unless a human has approved it."))


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf8"))


@server.tool()
def get_organisation() -> dict:
    """Organisation details, the review period, GST basis and the firm's review policies."""
    return load("organisation")


@server.tool()
def list_accounts() -> list:
    """Chart of accounts: code, name, type and default tax type."""
    return load("accounts")


@server.tool()
def list_contacts() -> list:
    """Contacts with ABN (TaxNumber), whether they are registered for GST, and their default account."""
    return load("contacts")


@server.tool()
def list_bank_transactions(account_code: str = "", contact: str = "", date_from: str = "", date_to: str = "") -> list:
    """Spend and receive money transactions for the period. Optional filters: account code, contact name
    (substring, case insensitive), and ISO dates."""
    out = []
    for t in load("bank_transactions"):
        li = t["LineItems"][0]
        if account_code and li["AccountCode"] != account_code:
            continue
        if contact and contact.lower() not in t["Contact"]["Name"].lower():
            continue
        if date_from and t["Date"] < date_from:
            continue
        if date_to and t["Date"] > date_to:
            continue
        out.append(t)
    return out


@server.tool()
def get_bank_statement() -> list:
    """Bank statement lines for the period, with the Xero transaction each one is matched to (or null)."""
    return load("bank_statement")


@server.tool()
def get_account_totals() -> list:
    """Net movement and GST per account for the period, built from the transactions (a trial balance view)."""
    acc = {a["Code"]: a for a in load("accounts")}
    net, gst = defaultdict(float), defaultdict(float)
    for t in load("bank_transactions"):
        li = t["LineItems"][0]
        sign = 1 if t["Type"] == "SPEND" else -1
        net[li["AccountCode"]] += sign * li["LineAmount"]
        gst[li["AccountCode"]] += sign * li["TaxAmount"]
    return [{"Code": c, "Name": acc[c]["Name"], "Type": acc[c]["Type"], "Net": round(net[c], 2), "GST": round(gst[c], 2)}
            for c in sorted(net)]


@server.tool()
def queue_review_item(id: str, category: str, issue: str, proposed_fix: str, evidence: str, confidence: str) -> dict:
    """Record one finding for human review. category is gst, coding or recon. confidence is high, medium or low.
    Nothing in Xero changes; this only adds a row to the review queue."""
    if category not in ("gst", "coding", "recon"):
        return {"ok": False, "error": "category must be gst, coding or recon"}
    row = {"id": id, "category": category, "issue": issue, "proposed_fix": proposed_fix, "evidence": evidence,
           "confidence": confidence, "queued_at": dt.datetime.now().isoformat(timespec="seconds")}
    with open(REVIEW / "queue.jsonl", "a", encoding="utf8") as f:
        f.write(json.dumps(row) + "\n")
    return {"ok": True, "queued": id}


@server.tool()
def post_manual_journal(journal_id: str, narration: str, lines: list) -> dict:
    """Post a manual journal to Xero. Refused unless a human has listed journal_id in review/approved.json."""
    approved = REVIEW / "approved.json"
    ok = approved.exists() and journal_id in json.loads(approved.read_text(encoding="utf8"))
    if not ok:
        return {"ok": False, "error": f"{journal_id} is not approved. A reviewer must add it to review/approved.json."}
    with open(REVIEW / "posted.jsonl", "a", encoding="utf8") as f:
        f.write(json.dumps({"journal_id": journal_id, "narration": narration, "lines": lines}) + "\n")
    return {"ok": True, "posted": journal_id}


if __name__ == "__main__":
    server.run("stdio")
