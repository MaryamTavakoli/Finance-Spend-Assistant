// AnswerCard: shows one answer from POST /ask, and what it is based on.
// From top to bottom:
//   1. "Based on" line: which policy sections and how many database queries were used
//   2. warnings from the backend's checks (e.g. a number that no query returned)
//   3. the answer itself (markdown, so tables and bold text display properly)
//   4. assumptions and limitations
//   5. policy evidence: the cited sections, quoted from the policy document
//   6. data evidence: every SQL query the agent ran, with its result table

import ReactMarkdown from "react-markdown";   // turns markdown text into HTML
import remarkGfm from "remark-gfm";           // adds support for markdown tables
import DataTable from "./DataTable";

export default function AnswerCard({ result }) {
  // policy_evidence is an object {"4.1": "4.1 Payments may...", ...};
  // Object.entries turns it into a list of pairs: [["4.1", "4.1 Payments may..."], ...]
  const sections = Object.entries(result.policy_evidence);
  const queries = result.data_evidence;   // [{sql, columns, rows, truncated} or {sql, error}, ...]

  return (
    <div>
      {/* 1. Based on: policy §2, §4.1 · 3 database queries */}
      <p className="small">
        Based on: {sections.length ? "policy " + sections.map(([s]) => "§" + s).join(", ") : "no policy sections"}
        {" · "}
        {queries.length} database {queries.length === 1 ? "query" : "queries"}
      </p>

      {/* 2. Warnings (usually none) */}
      {result.warnings.map((w) => <p key={w} className="warning">⚠ {w}</p>)}

      {/* 3. The answer */}
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>

      {/* 4. Assumptions. "condition && (...)" means: only show this part if the condition is true.
             <> ... </> groups elements without adding an extra box to the page. */}
      {result.assumptions.length > 0 && (
        <>
          <h4>Assumptions</h4>
          <ul>{result.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}

      {/* 5. Policy evidence: the text comes from the policy file, not from the AI */}
      {sections.length > 0 && (
        <>
          <h4>Policy evidence (FIN-POL-014, quoted from the document)</h4>
          {sections.map(([s, text]) => (
            <blockquote key={s}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
            </blockquote>
          ))}
        </>
      )}

      {/* 6. Data evidence: one fold-out per query, with the SQL and its result (or its error) */}
      {queries.length > 0 && (
        <>
          <h4>Data evidence (the SQL that ran and its results)</h4>
          {queries.map((q, i) => (
            <details key={i}>
              <summary>
                Query {i + 1}
                {/* "· 12 rows", "· 200+ rows" if cut off, or "· error" */}
                {q.error ? " · error" : ` · ${q.rows.length}${q.truncated ? "+" : ""} rows`}
              </summary>
              <pre>{q.sql}</pre>
              {q.error ? <p className="error">{q.error}</p> : <DataTable columns={q.columns} rows={q.rows} />}
            </details>
          ))}
        </>
      )}
    </div>
  );
}
