"""
eval.py: a small test of answer quality. Run from backend/:  python eval.py

Each case asks the agent a question whose correct answer we already know:
  - number cases: the correct number is computed with our own fixed SQL
  - policy cases: we know which policy section answers the question
A case passes if the answer is right AND has no warnings.
Note: every case calls OpenAI, so one run costs a few cents and takes a few minutes.
"""

from agent import ask, numbers_in
from database import run_query

def known(sql):
    """Run our own trusted SQL and return the numbers in its first row, rounded to 2 decimals."""
    row = run_query(sql)["rows"][0]
    return [round(float(x), 2) for x in row]

# (question, SQL that computes the correct answer)
NUMBER_CASES = [
    ("How many invoices are there in total?",
     "SELECT COUNT(*) FROM invoices"),
    ("What is the net EUR spend?",
     "SELECT SUM(amount) FROM invoices WHERE currency = 'EUR'"),
    ("How many invoices have no approver?",
     "SELECT COUNT(*) FROM invoices WHERE approved_by IS NULL"),
    ("How many EUR invoices of 1,000 or more have no purchase order?",
     "SELECT COUNT(*) FROM invoices WHERE currency = 'EUR' AND amount >= 1000 AND po_number IS NULL"),
    ("What is the net GBP spend with vendors that are ON_HOLD?",
     """SELECT SUM(i.amount) FROM invoices i JOIN vendors v USING (vendor_id)
        WHERE v.status = 'ON_HOLD' AND i.currency = 'GBP'"""),
]

# (question, the policy section that answers it)
POLICY_CASES = [
    ("Who needs to approve an invoice of EUR 60,000?", "3"),
    ("Can we pay an invoice from a vendor that is ON_HOLD?", "4.1"),
    ("How long must procurement records be kept?", "8.1"),
]
def cited(result, section):
    """True if the answer cited this section, its parent or one of its clauses
    (e.g. for "4.1", citing "4" or "4.1" counts)."""
    top = section.split(".")[0]                         # "4.1" -> "4"
    return any(s.split(".")[0] == top for s in result["policy_evidence"])


def report(ok, question, expected, result):
    """Print one PASS/FAIL line, plus details when it fails."""
    print(f"{'PASS' if ok else 'FAIL'}  {question}  (expected {expected})")
    if not ok:
        print("      answer:  ", result["answer"][:200].replace("\n", " "))
        print("      cited:   ", list(result["policy_evidence"]))
        print("      warnings:", result["warnings"])


if __name__ == "__main__":
    passed = total = 0

    print("== Number cases ==")
    for question, sql in NUMBER_CASES:
        expected = known(sql)
        r = ask(question)
        ok = all(x in numbers_in(r["answer"]) for x in expected) and not r["warnings"]
        report(ok, question, expected, r)
        passed, total = passed + ok, total + 1

    print("\n== Policy cases ==")
    for question, section in POLICY_CASES:
        r = ask(question)
        ok = cited(r, section) and not r["warnings"]
        report(ok, question, "§" + section, r)
        passed, total = passed + ok, total + 1

    print(f"\n{passed}/{total} passed")