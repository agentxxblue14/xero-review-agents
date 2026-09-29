---
name: xero-month-review
description: Review one month of an Australian client's Xero books for GST, coding and reconciliation errors before the month-end pack is built. Use when asked to review, check or close a client's month in Xero.
---

# Xero month review (AU)

The review rules the three reviewer agents share. The firm owns these rules; change them here,
not inside an agent, so every agent reads the same version.

## Ground rules

- Read everything through the `xero` MCP tools. Never guess a figure you have not read.
- Every finding goes to `queue_review_item` with the transaction or statement line id, the evidence
  (the fields you read), a proposed fix and a confidence. One finding per id and category.
- Never post a journal. `post_manual_journal` is for after a human approves, and a hook blocks it.
- If a rule below does not settle it, queue it as `low` confidence and say what you would ask the
  client. A question is a valid finding; a guess is not.

## GST (category `gst`)

| Check | Rule |
|---|---|
| Tax rate fits the account | Wages, super, drawings, interest income and bank transfers are BAS Excluded. Bank fees are input taxed: no GST credit. |
| Supplier can charge GST | A GST credit needs a supplier registered for GST (`IsGSTRegistered` true). Otherwise the line is GST free and the credit reverses. |
| Overseas suppliers | No GST charged means no GST credit. GST free coding is correct, not an error. |
| The maths | On a GST line, TaxAmount must equal Total / 11 to the cent. 10% of the total is the classic mistake. |
| Private or no business purpose | No GST credit on private spending. If the coding reviewer would query a line as private, the GST credit on it is a separate `gst` finding. |

## Coding (category `coding`)

| Check | Rule |
|---|---|
| Capital items | Anything over the organisation's `CapitaliseThreshold` that lasts more than a year goes to a fixed asset account, not an expense. At or under the threshold, expensing is correct. |
| Job costs | Subcontractor progress claims go to Subcontractors (315), goods to Materials (310). Job costing depends on the split. |
| Private spending | Groceries, personal subscriptions and similar on the company account are queried and likely go to Owner Drawings with no GST. |
| Prepayments | A bill covering more than the current month (insurance, annual licences over the threshold) goes to Prepayments and is released monthly. Work the monthly release from the ex-GST amount. |

## Reconciliation (category `recon`)

| Check | Rule |
|---|---|
| Duplicates | Same contact, same total and the same invoice number in any format (`INV 88412` = `88412`) is one bill entered twice. The copy not on the bank statement is the duplicate. |
| Amount mismatch | A matched statement line whose amount differs from the transaction total is an error on one side. Queue it under the Xero transaction id (the thing that gets corrected), quote the statement line id in the evidence, and say what to check. |
| Unmatched statement lines | A statement line with no Xero transaction is missing from the books. Say what it most likely is and what evidence would confirm it. |
| Unreconciled transactions | A transaction not on the statement is either a duplicate or a timing difference. Say which. |

## What counts as done

Every transaction and statement line has been read by at least one reviewer, every finding is in the
queue, and nothing was posted to Xero.
