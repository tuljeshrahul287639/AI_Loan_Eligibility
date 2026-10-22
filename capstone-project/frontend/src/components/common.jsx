export const STATUS_LABELS = {
  APPROVED: "Approved",
  REJECTED: "Rejected",
  PENDING_REVIEW: "Pending review",
};

export function StatusBadge({ status }) {
  const className = {
    APPROVED: "badge approve",
    REJECTED: "badge reject",
    PENDING_REVIEW: "badge review",
  }[status] || "badge";
  return <span className={className}>{STATUS_LABELS[status] || status}</span>;
}

export function formatPercent(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—";
}

// Indian rupees with Indian digit grouping, e.g. ₹2,50,000
export function formatMoney(value) {
  return typeof value === "number"
    ? value.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
    : "—";
}

export function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

function prettyKey(key) {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// Fields that hold rupee amounts, so they are shown as ₹ values
const MONEY_KEYS = new Set([
  "monthly_income",
  "monthly_expenses",
  "existing_debts",
  "loan_amount",
  "monthly_payment",
]);

function formatValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return <code>{JSON.stringify(value)}</code>;
  if (MONEY_KEYS.has(key) && typeof value === "number") return formatMoney(value);
  return String(value);
}

/** Renders every key of a plain object so nothing is hidden from the user. */
export function KeyValueTable({ data, emptyText = "No data" }) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return <p className="muted">{emptyText}</p>;

  return (
    <table className="kv-table">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <th>{prettyKey(key)}</th>
            <td>{formatValue(key, value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
