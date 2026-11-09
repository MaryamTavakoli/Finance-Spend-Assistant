# Finance Spend Assistant

A small web app where a finance analyst can ask questions about the 2025 invoices,
the vendor master and the procurement policy. Every answer shows what it is based on:
the policy sections it relies on and the exact SQL queries and rows behind every number.

## Architecture

- **Frontend:** React (built and served with Vite)
- **Backend:** FastAPI
- **Database:** DuckDB, in memory, loaded from the two CSV files at startup
- **AI:** LangChain agent with OpenAI `gpt-5` (`reasoning_effort="low"`)

## Setup

**Requirements:** Python 3.12, Node.js, and an OpenAI API key.

1. **Create and activate a virtual environment** (in the project root):
   ```bash
   uv venv .venv --python 3.12
   source .venv/bin/activate
   ```

2. **Install the Python packages:**
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Add your OpenAI API key.** Create a file `backend/.env` containing:
   ```
   OPENAI_API_KEY=your-key-here
   ```
   This file is in `.gitignore` and is never committed.

4. **Start the backend** (in a terminal with the virtual environment active):
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000
   ```
   Open http://localhost:8000/docs to try the endpoints in the browser.

5. **Start the frontend** (in a second terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173.

### Tests (optional)

Run these from `backend/` with the virtual environment active:

| Command | What it checks |
|---|---|
| `python database.py` | **Security:** invalid queries, multiple queries and attack queries (DELETE, DROP, reading other files...) are all blocked. |
| `python agent.py` | **Answer check:** fabricated numbers are detected; policy citations are validated against actual sections; the full agent pipeline is tested. |
| `python eval.py` | **Answer quality:** 8 questions with known correct answers (5 numbers computed with our own SQL, 3 policy sections) are compared with the agent's answers. |

## How it works

### Project map

| File | Role |
|---|---|
| `backend/database.py` | Loads the CSVs into DuckDB, locks it, and runs only single read-only SELECT queries |
| `backend/agent.py` | The AI pipeline: prompt, agent, `execute_sql_query` tool, and the answer checks |
| `backend/main.py` | The API: `GET /summary` (fixed SQL, no AI) and `POST /ask` (the agent) |
| `backend/eval.py` | The eval set and scoring script |
| `frontend/src/api.js` | The only file that calls the backend |
| `frontend/src/App.jsx` | The page: chat state, loading and error handling |
| `frontend/src/SummaryPanel.jsx` | Summary panel, loaded on startup from `GET /summary` |
| `frontend/src/AnswerCard.jsx` | One answer with its evidence |
| `frontend/src/DataTable.jsx` | Draws any query result as a table |
| `notebooks/finance_agent.ipynb` | The prototype where the pipeline was built and tested step by step |

### AI pipeline

One LangChain agent (`create_agent`) with:
- **LLM:** OpenAI `gpt-5`, `reasoning_effort="low"`.
- **System prompt:** the rules, a description of the tables built from the real data
  (columns, types, NULL counts and the actual values of short lists such as vendor status),
  and the **full policy**. The policy is only about 50 lines, so no vector database is needed.
- **One tool, `execute_sql_query`:** runs one SQL query. The agent decides whether it needs it:
  a policy-only question is answered from the system prompt with no queries, and a data
  question gets one or more queries. If a query fails, the error is returned to the agent
  so it can fix the query and retry.
- **Structured response:** answer (markdown), cited policy sections, assumptions.

### Safety: the agent can only read the two tables

- `run_query` accepts exactly **one `SELECT` statement**. DELETE, UPDATE, DROP, multiple
  statements and so on are rejected before they run.
- After loading the CSVs, DuckDB is **locked**: no access to files or the internet, and
  no query can change that setting back.
- Results are capped at 200 rows. The agent is limited to about 9 tool calls per question.

### Reliability: checks on every answer

- All arithmetic is done in SQL, not by the LLM. Currencies are never added together,
  because there are no exchange rates in the data.
- **Number check:** every number in the answer must appear in a query result, the policy
  or the question. Otherwise the answer shows a warning.
- **Citation check:** cited sections must exist in the policy. The policy text shown to the
  analyst is quoted from the document by the server, not written by the LLM.
- Every question is written to an audit log line (question, SQL, sections, warnings),
  following policy §8.2.

### What the UI shows for each answer

- A "Based on" line: the policy sections and the number of queries.
- Any warnings.
- The answer, then the assumptions.
- The quoted policy sections.
- Every SQL query with its result table.

## Write-up

### What I Built

The AI system answers user questions by combining information from the provided Global Procurement & Spend Policy document with data retrieved from the CSV files through SQL queries.

My main priorities were safety, reliability, and transparency:

- Safety: The system has read-only access to the data. It can execute only validated SELECT queries, preventing modifications to the database or access to unauthorized resources.

- Reliability: SQL queries are validated before execution, and numerical values in the final answers are checked against actual query results to reduce the risk of hallucinations.

- Automated Evaluation (Optional Extra): I created a small evaluation set (backend/eval.py) with 8 questions and known correct answers: 5 numerical answers calculated using my own SQL queries, and 3 policy questions with their corresponding policy sections. A test passes only if the agent's answer includes the correct number (or cites the correct policy section) and contains no warnings. Result: 8/8 tests passed.

- Manual Evaluation: I manually tested 10 questions in a notebook (notebooks/finance_agent.ipynb), covering four categories: policy-only, data-only, policy-and-data, and out-of-scope questions. For each question, I reviewed the answer, assumptions, and supporting data evidence (SQL queries and their results). All answers were supported by the provided evidence, and the agent handled out-of-scope questions by acknowledging its limitations rather than guessing.

- Transparency: The system presents its assumptions, supporting evidence from the policy, and data evidence (executed SQL queries and their results), allowing users to understand how each answer was derived.

### What I Left Out

- Short-term memory: Each question is processed independently, even within the same session. The system does not support follow-up questions that depend on previous interactions.

- Long-term memory: The system does not retain information across sessions.

- Caching: Caching could reduce repeated LLM calls, token usage, costs, and latency for similar questions. This would require a strategy for normalizing questions and identifying equivalent queries before processing or caching them.

- Vector-based policy retrieval: Since the provided policy document is short, I included it directly in the system prompt. For larger policy documents, I would use embeddings and a vector database to retrieve relevant sections dynamically rather than passing the entire document to the LLM.

- Guardrail: Some information, such as currency conversion rates to EUR (Policy §5.1), requester details (Policy §7), receipt dates (Policy §5.2), exception register entries (Policy §9.1), and due-diligence status (Policy §4.2), is not available in the data. Currently, the agent is instructed through the system prompt to acknowledge these limitations rather than make up answers. However, this is a prompt-level instruction, not an independently enforced guardrail. A dedicated guardrail could detect questions requiring unavailable data before executing SQL queries and return an appropriate response.

### How I'd evaluate it

- SQL guard effectiveness: Measure the rate of invalid SQL queries that bypass the guards by testing the guarded run_sql function directly, without involving the LLM.

- Warning rate: Measure the percentage of responses with a non-empty warnings list, indicating invalid policy citations or unverified numbers.

- Guardrail effectiveness (if implemented): Measure how often the guardrail fails to identify questions requiring unavailable data before SQL execution.

- End-to-end answer accuracy: Evaluate the full pipeline against a test set of questions with known correct answers, measuring the success and failure rates. `eval.py` is a first version of this; I would grow it with the example questions from the brief, "can't answer" questions (e.g. requester, FX), and run each case several times to measure consistency, since LLM answers can vary between runs. This matters because the number check only proves that a number came from a query, not that it was the right query.

- Real-user feedback: Collect feedback from analysts to evaluate answer usefulness, clarity, and overall system reliability.

### What production would need

- Production database: Replace CSV-based, in-memory DuckDB with a production database where appropriate, using read-only credentials, query timeouts, and connection pooling.
- Authentication and authorization: Use SSO for user authentication and enforce database-, table-, or row-level permissions based on user roles.
- Audit trail: Persist user questions, SQL queries, execution status, policy citations, and validation warnings in secure, durable logs, with retention aligned with company policy.
- Cost management: Implement caching, per-user rate limits, appropriate model selection, and token/cost tracking.
- Quality assurance: Run automated regression tests after changes to prompts, models, or code, including SQL safety, citation validation, numerical verification, and answer accuracy.
- Scalability: Support concurrent requests through asynchronous API handling, multiple application workers, database connection management, and LLM concurrency limits.
- Monitoring: Track response latency, errors, resource usage, LLM costs, and system reliability.
- Data management: Keep financial data and policy documents up to date, with appropriate versioning and access controls.

### What I'd do next

I'd add guardrails, implement chat history to support follow-up questions, and expand the evaluation set to cover more scenarios and edge cases.