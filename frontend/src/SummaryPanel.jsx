// SummaryPanel: the left-hand panel with total spend by currency and by vendor status.
// It loads GET /summary once when the page opens, and shows one of three states:
//   loading -> "Loading summary…"
//   error   -> the error message and a Retry button
//   done    -> the overview line, two tables, and the SQL behind them

import { useEffect, useState } from "react";
import { getSummary } from "./api";
import DataTable from "./DataTable";

export default function SummaryPanel() {
  // useState creates a value that, when changed with its setter, makes React redraw the panel.
  const [data, setData] = useState(null);     // the /summary result, or null while loading
  const [error, setError] = useState(null);   // an error message, or null if all is fine

  // Fetch the summary. Used on page open and by the Retry button.
  function load() {
    setError(null);
    setData(null);                            // back to "loading"
    getSummary().then(setData).catch((e) => setError(e.message));
  }

  // useEffect(fn, []) runs fn once, right after the panel first appears on the page.
  useEffect(load, []);

  // --- error state ---
  if (error) {
    return (
      <div>
        <h2>Summary</h2>
        <p className="error">{error}</p>
        <button onClick={load}>Retry</button>
      </div>
    );
  }

  // --- loading state ---
  if (!data) return <div><h2>Summary</h2><p className="small">Loading summary…</p></div>;

  // --- done state ---
  // The overview query returns a single row; unpack its four values by position.
  const [invoices, vendors, firstDate, lastDate] = data.overview.rows[0];

  return (
    <div>
      <h2>Summary</h2>
      <p>
        <b>{invoices}</b> invoices from <b>{vendors}</b> vendors, {firstDate} to {lastDate}.
      </p>
      <p className="small">Amounts are per currency (no FX conversion) and net of credit notes.</p>

      {/* {...block} passes block.columns and block.rows (and the rest) as props to DataTable */}
      <h3>Net spend by currency</h3>
      <DataTable {...data.spend_by_currency} />

      <h3>Net spend by vendor status</h3>
      <DataTable {...data.spend_by_vendor_status} />

      {/* <details> is a built-in HTML fold-out: closed by default, click to open. */}
      <details>
        <summary>How these numbers were computed (SQL)</summary>
        {Object.values(data).map((block) => <pre key={block.sql}>{block.sql}</pre>)}
      </details>
    </div>
  );
}
