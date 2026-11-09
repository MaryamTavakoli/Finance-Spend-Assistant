// DataTable: draws a query result as an HTML table.
// It receives the same shape the backend sends for every query:
//   columns = ["currency", "net_spend"]
//   rows    = [["EUR", 4493726.12], ["GBP", 81200.5]]
// Used by the summary panel and by the "data evidence" part of each answer.

export default function DataTable({ columns, rows }) {
  return (
    <table>
      <thead>
        {/* one header cell per column name */}
        <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {/* one table row per data row, one cell per value.
            key={...} is an id React needs to keep track of items in a list. */}
        {rows.map((row, i) => (
          <tr key={i}>
            {row.map((value, j) => <td key={j}>{format(value)}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Turn one value into display text:
//   null      -> "—"            (e.g. an invoice with no purchase order)
//   140       -> "140"          whole numbers, with thousands separators
//   4493726.1 -> "4,493,726.10" decimals, always with 2 digits (money)
//   anything else (text, dates) is shown as it is
function format(value) {
  if (value === null) return "—";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("en-US")
      : value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return String(value);
}
