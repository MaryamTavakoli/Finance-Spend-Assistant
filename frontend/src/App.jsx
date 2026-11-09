// App: the whole page.
//   left:  the SummaryPanel (loads by itself when the page opens)
//   right: the chat: example questions, each question with its answer, and the input box
//
// Each question is a "turn" that moves through these states:
//   pending -> done   (show the AnswerCard)
//           -> error  (show the message and a Retry button)

import { useState } from "react";
import { askQuestion } from "./api";
import SummaryPanel from "./SummaryPanel";
import AnswerCard from "./AnswerCard";

// Clickable example questions, shown before the first question is asked.
const EXAMPLES = [
  "What are the top 5 vendors by spend?",
  "Which EUR invoices of 1,000 or more have no purchase order?",
  "Who needs to approve an invoice of EUR 60,000?",
  "How many invoices are from vendors that are not ACTIVE?",
];

export default function App() {
  const [turns, setTurns] = useState([]);   // list of turns: {id, question, status, result, error}
  const [input, setInput] = useState("");   // the text currently typed in the input box

  // While a question is being answered, we don't accept a new one.
  const busy = turns.some((t) => t.status === "pending");

  // Change some fields of one turn (found by its id) and leave the others as they are.
  // { ...t, ...changes } = a copy of t with the fields in "changes" replaced.
  function updateTurn(id, changes) {
    setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...changes } : t)));
  }

  // Ask the backend and store the outcome in the turn.
  async function run(id, question) {
    try {
      const result = await askQuestion(question);
      updateTurn(id, { status: "done", result });
    } catch (e) {
      updateTurn(id, { status: "error", error: e.message });
    }
  }

  // Called by the Ask button, the Enter key and the example buttons.
  function submit(text) {
    const question = text.trim();
    if (!question || busy) return;          // ignore empty questions, or while busy
    const id = Date.now();                  // the current time in ms: a simple unique id
    setTurns((all) => [...all, { id, question, status: "pending" }]);   // add the new turn at the end
    setInput("");                           // clear the input box
    run(id, question);
  }

  // Ask the same question again after an error.
  function retry(turn) {
    updateTurn(turn.id, { status: "pending", error: null });
    run(turn.id, turn.question);
  }

  return (
    <div>
      <header><h1>Finance Spend Assistant</h1></header>
      <main>
        <aside><SummaryPanel /></aside>

        <section className="chat">
          {/* Before the first question: a short intro and the example buttons */}
          {turns.length === 0 && (
            <div className="card">
              <p>Ask about the 2025 invoices, vendors or the procurement policy. For example:</p>
              {EXAMPLES.map((q) => (
                <button key={q} className="example" onClick={() => submit(q)}>{q}</button>
              ))}
            </div>
          )}

          {/* One card per question, showing its current state */}
          {turns.map((t) => (
            <div key={t.id} className="card">
              <p className="question">{t.question}</p>
              {t.status === "pending" && <p className="small">Thinking… (usually 10–40 seconds)</p>}
              {t.status === "error" && (
                <p className="error">
                  {t.error} <button onClick={() => retry(t)}>Retry</button>
                </p>
              )}
              {t.status === "done" && <AnswerCard result={t.result} />}
            </div>
          ))}

          {/* The input box. e.preventDefault() stops the browser from reloading the page,
              which is what a form does by default when submitted. */}
          <form onSubmit={(e) => { e.preventDefault(); submit(input); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}   // keep "input" in sync with what is typed
              placeholder={busy ? "Waiting for the answer…" : "Ask a question…"}
              maxLength={1000}                             // same limit as the backend
              disabled={busy}
            />
            <button disabled={busy || !input.trim()}>Ask</button>
          </form>
        </section>
      </main>
    </div>
  );
}
