"""Builds one month of Xero-shaped books for an invented AU company, with planted errors.

Everything here is invented. The output mirrors the shape of Xero API objects
(BankTransactions, Invoices, Accounts, Contacts) closely enough that swapping the
fixture loader for the real Xero API is a change to one module, not to the agents.

Run:  python data/build_fixtures.py
Writes: data/xero/*.json  and  evals/answer_key.json
"""
import json, random, pathlib, datetime as dt

random.seed(26)
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "xero"
OUT.mkdir(exist_ok=True)
EVAL = ROOT.parent / "evals"
EVAL.mkdir(exist_ok=True)

ORG = {"Name": "Harbourline Interiors Pty Ltd (DEMO)", "BaseCurrency": "AUD", "CountryCode": "AU",
       "PeriodStart": "2026-08-01", "PeriodEnd": "2026-08-31", "GSTBasis": "ACCRUALS",
       "Policies": {"CapitaliseThreshold": 1000.00, "RequireABNForGSTCredit": True}}

ACCOUNTS = [
    ("090", "Business Bank Account", "BANK", "BASEXCLUDED"),
    ("200", "Sales: Fitout Contracts", "REVENUE", "OUTPUT"),
    ("260", "Other Revenue", "REVENUE", "OUTPUT"),
    ("270", "Interest Income", "REVENUE", "BASEXCLUDED"),
    ("310", "Materials", "DIRECTCOSTS", "INPUT"),
    ("315", "Subcontractors", "DIRECTCOSTS", "INPUT"),
    ("404", "Bank Fees", "EXPENSE", "EXEMPTEXPENSES"),
    ("408", "Cleaning", "EXPENSE", "INPUT"),
    ("412", "Consulting & Accounting", "EXPENSE", "INPUT"),
    ("420", "Entertainment", "EXPENSE", "INPUT"),
    ("433", "Insurance", "EXPENSE", "INPUT"),
    ("445", "Light, Power, Heating", "EXPENSE", "INPUT"),
    ("449", "Motor Vehicle Expenses", "EXPENSE", "INPUT"),
    ("469", "Rent", "EXPENSE", "INPUT"),
    ("473", "Repairs and Maintenance", "EXPENSE", "INPUT"),
    ("477", "Wages and Salaries", "EXPENSE", "BASEXCLUDED"),
    ("478", "Superannuation", "EXPENSE", "BASEXCLUDED"),
    ("485", "Subscriptions", "EXPENSE", "INPUT"),
    ("489", "Telephone & Internet", "EXPENSE", "INPUT"),
    ("620", "Prepayments", "CURRENT", "BASEXCLUDED"),
    ("710", "Office Equipment", "FIXED", "INPUT"),
    ("720", "Computer Equipment", "FIXED", "INPUT"),
    ("880", "Owner A Drawings", "EQUITY", "BASEXCLUDED"),
]
ACCOUNTS = [{"Code": c, "Name": n, "Type": t, "TaxType": tx} for c, n, t, tx in ACCOUNTS]
ACC = {a["Code"]: a for a in ACCOUNTS}

CONTACTS = [
    ("Bunnings Trade", "63 008 672 179", True, "310"),
    ("Reece Plumbing Supply", "49 004 313 133", True, "310"),
    ("Laminex Direct", "15 000 002 222", True, "310"),
    ("Coastal Electrical Contractors", "22 611 402 918", True, "315"),
    ("Pinewood Joinery", "31 609 110 541", True, "315"),
    ("Ridge Tiling (sole trader)", "71 824 330 016", False, "315"),
    ("Metro Waste Services", "58 112 900 311", True, "408"),
    ("Ausgrid Energy", "67 505 337 385", True, "445"),
    ("Telstra", "33 051 775 556", True, "489"),
    ("Coles Express", "45 004 189 708", True, "449"),
    ("QBE Insurance", "78 003 191 035", True, "433"),
    ("Keystone Property Trust", "18 620 441 902", True, "469"),
    ("Hartwell CFO Advisory", "90 633 180 227", True, "412"),
    ("Xero Australia", "57 111 000 222", True, "485"),
    ("Atlassian (overseas)", "", False, "485"),
    ("JB Hi-Fi Business", "37 093 114 286", True, "720"),
    ("Officeworks", "36 004 763 526", True, "710"),
    ("Woolworths", "88 000 014 675", True, "420"),
    ("Commonwealth Bank", "48 123 123 124", True, "404"),
    ("Payroll Clearing", "", False, "477"),
    ("AustralianSuper", "65 714 394 898", False, "478"),
    ("Brightwater Dental Group", "12 345 678 901", True, "200"),
    ("Northside Physio Pty Ltd", "23 456 789 012", True, "200"),
    ("Kestrel Cafe Group", "34 567 890 123", True, "200"),
]
CONTACTS = [{"ContactID": f"C{i:03d}", "Name": n, "TaxNumber": abn, "IsGSTRegistered": gst, "DefaultAccountCode": acc}
            for i, (n, abn, gst, acc) in enumerate(CONTACTS, 1)]
CON = {c["Name"]: c for c in CONTACTS}

txns, stmt, key = [], [], {"planted": [], "must_not_flag": []}
n = 0


def gst_of(total, taxtype):
    return round(total / 11, 2) if taxtype in ("INPUT", "OUTPUT") else 0.0


def add(date, contact, desc, acc, total, kind="SPEND", taxtype=None, gst=None, reconciled=True,
        on_statement=True, stmt_amount=None, ref=None):
    global n
    n += 1
    tid = f"BT-{n:04d}"
    tt = taxtype or ACC[acc]["TaxType"]
    g = gst_of(total, tt) if gst is None else gst
    txns.append({"BankTransactionID": tid, "Type": kind, "Date": date, "Contact": {"Name": contact},
                 "Reference": ref or "", "LineItems": [{"Description": desc, "AccountCode": acc, "TaxType": tt,
                 "LineAmount": round(total - g, 2), "TaxAmount": g}], "Total": total, "IsReconciled": reconciled})
    if on_statement:
        amt = stmt_amount if stmt_amount is not None else total
        stmt.append({"StatementLineID": f"SL-{len(stmt) + 1:04d}", "Date": date,
                     "Payee": contact.upper()[:22], "Amount": round(-amt if kind == "SPEND" else amt, 2),
                     "MatchedTransactionID": tid if reconciled else None})
    return tid


def plant(tid, category, issue, fix):
    key["planted"].append({"id": tid, "category": category, "issue": issue, "expected_fix": fix})


def trap(tid, why):
    key["must_not_flag"].append({"id": tid, "why_it_is_correct": why})


d = lambda day: f"2026-08-{day:02d}"

# Clean, routine month
for day in (3, 10, 17, 24, 31):
    add(d(day), "Payroll Clearing", "Weekly wages", "477", round(random.uniform(9800, 11200), 2))
add(d(28), "AustralianSuper", "Super guarantee, July", "478", 4312.40)
add(d(1), "Keystone Property Trust", "Rent, workshop, August", "469", 5390.00)
add(d(12), "Ausgrid Energy", "Electricity, July", "445", 612.37)
add(d(14), "Telstra", "Mobiles and NBN", "489", 318.90)
add(d(19), "Metro Waste Services", "Skip bin, 2 lifts", "408", 880.00)
add(d(22), "Hartwell CFO Advisory", "Bookkeeping and advisory, July", "412", 2750.00)
add(d(5), "Xero Australia", "Xero subscription", "485", 99.00)
for day in (2, 6, 9, 13, 16, 20, 23, 27, 30):
    add(d(day), "Coles Express", "Fuel, work ute", "449", round(random.uniform(85, 160), 2))
for day in (4, 7, 11, 15, 18, 21, 25, 29):
    sup = random.choice(["Bunnings Trade", "Reece Plumbing Supply", "Laminex Direct"])
    add(d(day), sup, "Materials, job " + random.choice(["J-118", "J-121", "J-124", "J-127"]), "310",
        round(random.uniform(420, 3900), 2))
for day in (8, 15, 22, 29):
    sub = random.choice(["Coastal Electrical Contractors", "Pinewood Joinery"])
    add(d(day), sub, "Progress claim, job " + random.choice(["J-118", "J-121", "J-124"]), "315",
        round(random.uniform(2400, 8800), 2))
for day, cust, amt in ((6, "Brightwater Dental Group", 38500.00), (13, "Northside Physio Pty Ltd", 21780.00),
                       (20, "Kestrel Cafe Group", 16940.00), (27, "Brightwater Dental Group", 27500.00)):
    add(d(day), cust, "Progress claim received", "200", amt, kind="RECEIVE")

# Things that look wrong but are right (false-positive traps)
trap(add(d(5), "Atlassian (overseas)", "Jira subscription (overseas supplier)", "485", 138.60,
         taxtype="EXEMPTEXPENSES", gst=0.0),
     "Overseas supplier, no GST charged, so no GST credit. GST-free coding is correct.")
trap(add(d(31), "Commonwealth Bank", "Interest earned", "270", 41.18, kind="RECEIVE"),
     "Interest income is input taxed / BAS excluded. Correct as coded.")
trap(add(d(18), "Officeworks", "Office chair", "473", 649.00),
     "Under the $1,000 capitalise threshold, so expensing it is the firm's policy.")
trap(add(d(31), "Commonwealth Bank", "Account keeping fee", "404", 10.00),
     "Bank fee coded to Bank Fees with no GST. Correct.")

# Planted errors
plant(add(d(31), "Commonwealth Bank", "Merchant facility fee", "404", 64.90, taxtype="INPUT"),
      "gst", "Bank fee coded with GST on Expenses; bank fees are input taxed, no GST credit.",
      "Change tax rate to GST Free Expenses / input taxed; GST claimed 5.90 reverses.")
plant(add(d(26), "Ridge Tiling (sole trader)", "Tiling, job J-121", "315", 3960.00, taxtype="INPUT"),
      "gst", "GST credit claimed on a bill from a supplier not registered for GST.",
      "Code as GST Free Expenses; 360.00 GST credit is not claimable. Ask supplier for a tax invoice only if they have since registered.")
plant(add(d(17), "Payroll Clearing", "Weekly wages (casual)", "477", 3300.00, taxtype="INPUT"),
      "gst", "Wages coded with GST on Expenses; wages are BAS excluded.",
      "Change tax rate to BAS Excluded; 300.00 GST credit reverses.")
plant(add(d(9), "Laminex Direct", "Benchtop laminate, job J-124", "310", 2178.00, gst=217.80),
      "gst", "GST is 217.80, which is 10% of the total, not 1/11. Should be 198.00.",
      "Correct GST to 198.00 so net is 1,980.00.")
plant(add(d(16), "JB Hi-Fi Business", "Laptop for estimator", "473", 2899.00),
      "coding", "2,899 laptop expensed to Repairs and Maintenance; over the 1,000 capitalise threshold.",
      "Recode to 720 Computer Equipment and depreciate.")
plant(add(d(22), "Pinewood Joinery", "Joinery install, job J-118", "310", 6380.00),
      "coding", "Subcontractor progress claim coded to Materials.",
      "Recode to 315 Subcontractors so job cost splits stay right.")
groceries = add(d(23), "Woolworths", "Groceries", "420", 214.35)
plant(groceries, "coding", "Grocery shop on the company card, no business purpose on the receipt.",
      "Query the owner; likely 880 Owner A Drawings with no GST.")
# Added to the key after run 1: the GST reviewer rightly flagged the GST credit on the same line.
plant(groceries, "gst", "Full GST credit claimed on groceries with no business purpose.",
      "If private, no GST credit: 19.49 reverses with the recode to drawings.")
plant(add(d(2), "QBE Insurance", "Contract works insurance, 12 months to 31 Jul 2027", "433", 5280.00),
      "coding", "Twelve months of insurance expensed in August.",
      "Code to 620 Prepayments and release 400.00 a month, 1/12 of the ex-GST 4,800.00.")
dup_a = add(d(11), "Reece Plumbing Supply", "Materials, job J-121", "310", 1848.00, ref="INV 88412")
dup_b = add(d(12), "Reece Plumbing Supply", "Materials, J-121", "310", 1848.00, ref="88412", on_statement=False,
            reconciled=False)
plant(dup_b, "recon", "Duplicate of " + dup_a + ": same supplier, amount and invoice number, not on the bank statement.",
      "Delete the duplicate; 1,848.00 of cost and 168.00 of GST are double counted.")
t = add(d(24), "Coastal Electrical Contractors", "Progress claim, job J-124", "315", 1254.00, stmt_amount=1524.00)
plant(t, "recon", "Recorded as 1,254.00 but the bank paid 1,524.00 (digits transposed).",
      "Correct to 1,524.00 against the supplier's claim; check the claim first.")
# Statement line with no transaction in Xero
stmt.append({"StatementLineID": f"SL-{len(stmt) + 1:04d}", "Date": d(28), "Payee": "ATO PAYMENT",
             "Amount": -8420.00, "MatchedTransactionID": None})
key["planted"].append({"id": stmt[-1]["StatementLineID"], "category": "recon",
                       "issue": "8,420.00 ATO payment on the bank statement with nothing in Xero.",
                       "expected_fix": "Code to the ATO integrated client account after checking the BAS it pays; not an expense."})

json.dump(ORG, open(OUT / "organisation.json", "w"), indent=1)
json.dump(ACCOUNTS, open(OUT / "accounts.json", "w"), indent=1)
json.dump(CONTACTS, open(OUT / "contacts.json", "w"), indent=1)
json.dump(txns, open(OUT / "bank_transactions.json", "w"), indent=1)
json.dump(stmt, open(OUT / "bank_statement.json", "w"), indent=1)
json.dump(key, open(EVAL / "answer_key.json", "w"), indent=1)
print(f"{len(txns)} transactions, {len(stmt)} statement lines, {len(key['planted'])} planted errors, "
      f"{len(key['must_not_flag'])} traps")
