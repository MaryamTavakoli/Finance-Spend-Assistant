"""
main.py: the web API (FastAPI). The React page talks to these two endpoints:

  GET  /summary   fixed spend totals, computed with plain SQL (no AI). Loaded when the page opens.
  POST /ask       {"question": "..."} -> the agent's answer plus its evidence (from agent.py).

Run it from the backend/ folder:
  python -m uvicorn main:app --reload --port 8000
Then open http://localhost:8000/docs to try the endpoints in the browser.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import ask
from database import run_query

# Log messages go to the terminal where uvicorn runs, with a time stamp.
log = logging.getLogger("finance_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Finance Spend Assistant")

# CORS: browsers block a page on one address (localhost:5173, the React page) from calling
# another address (localhost:8000, this API) unless the API explicitly allows it. This allows it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------------------
# GET /summary
# ------------------------------------------------------------------------------------------
# Fixed questions don't need an LLM: plain SQL is faster, free and always gives the same answer.
SUMMARY_QUERIES = {
    # How much data there is: number of invoices and vendors, first and last invoice date.
    "overview": '''
        SELECT COUNT(*) AS invoices, COUNT(DISTINCT vendor_id) AS vendors,
               MIN(invoice_date) AS first_date, MAX(invoice_date) AS last_date
        FROM invoices''',
    # Total spend per currency (never mixed: there are no exchange rates). Credit notes are
    # negative amounts, so SUM gives net spend.
    "spend_by_currency": '''
        SELECT currency, COUNT(*) AS invoices, SUM(amount) AS net_spend
        FROM invoices GROUP BY currency ORDER BY net_spend DESC''',
    # Total spend per vendor status (ACTIVE / INACTIVE / ON_HOLD), still split by currency.
    "spend_by_vendor_status": '''
        SELECT v.status, i.currency, COUNT(*) AS invoices, SUM(i.amount) AS net_spend
        FROM invoices i JOIN vendors v USING (vendor_id)
        GROUP BY v.status, i.currency ORDER BY v.status, i.currency''',
}


@app.get("/summary")
def summary():
    """Run each summary query. Every block also returns its SQL, so the numbers are traceable.

    Result shape:
      {"overview": {"sql": "...", "columns": [...], "rows": [...], "truncated": false}, ...}
    """
    # " ".join(sql.split()) squeezes the SQL onto one line, for tidy display.
    return {name: {"sql": " ".join(sql.split()), **run_query(sql)}
            for name, sql in SUMMARY_QUERIES.items()}


# ------------------------------------------------------------------------------------------
# POST /ask
# ------------------------------------------------------------------------------------------
class AskRequest(BaseModel):
    """The request body. FastAPI checks it automatically: an empty or too-long question
    (or a missing one) is rejected with a 422 error before our code runs."""
    question: str = Field(min_length=1, max_length=1000)


@app.post("/ask")
def ask_endpoint(req: AskRequest):
    # Note: this is a plain "def", not "async def". FastAPI then runs it in a separate
    # thread, so a slow question (10-40 s) doesn't freeze the server for other users.
    try:
        result = ask(req.question)
    except Exception as e:
        # E.g. OpenAI is down or the API key is wrong. Log the full error for us, and send
        # a short message to the page (502 = "a service behind this server failed").
        log.exception("ask failed")
        raise HTTPException(status_code=502, detail=f"The assistant failed: {type(e).__name__}: {e}")

    result.pop("messages")   # LangChain message objects can't be sent as JSON (debug only)

    # Audit line (policy §8.2: traceable lineage): which question, which SQL, which sections.
    log.info("ask question=%r sql=%r sections=%r warnings=%r",
             req.question,
             [q["sql"] for q in result["data_evidence"]],
             list(result["policy_evidence"]),
             result["warnings"])
    return result
