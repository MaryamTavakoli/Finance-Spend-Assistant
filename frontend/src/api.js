// api.js: the only file that talks to the backend.
// Every other component calls getSummary() or askQuestion() and never deals with URLs or HTTP.

// Address of the FastAPI server (see backend/main.py).
const API_URL = "http://localhost:8000";

// Send one request and return the JSON body.
// If anything goes wrong, throw an Error with a message a person can read; the components
// catch it and show it on the page.
async function request(path, options) {
  let res;
  try {
    res = await fetch(API_URL + path, options);   // await = wait for the reply without freezing the page
  } catch {
    // fetch itself fails only when the server can't be reached at all
    throw new Error("Cannot reach the backend. Is it running on port 8000?");
  }

  // Read the reply as JSON. If it isn't valid JSON, use null instead of crashing.
  const body = await res.json().catch(() => null);

  if (!res.ok) {
    // The server answered with an error code (e.g. 422 or 502).
    // FastAPI puts the error message in "detail"; for 422 it's a list, so we fall back to a
    // generic message.
    const detail = body?.detail;   // ?. = "only if body is not null"
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return body;
}

// GET /summary: the fixed spend totals for the side panel.
export const getSummary = () => request("/summary");

// POST /ask: send a question, get back {answer, assumptions, policy_evidence, data_evidence, warnings}.
export const askQuestion = (question) =>
  request("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),   // -> '{"question": "..."}'
  });
