export const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Self-employed"];

/**
 * Controlled form for the applicant fields the agents need.
 * `sources` maps a field name to "document" when its value came from an extracted document.
 */
export default function ApplicationForm({ values, sources, onChange, onSubmit, submitting, disabled }) {
  function handleChange(event) {
    const { name, value, type, checked } = event.target;
    onChange(name, type === "checkbox" ? checked : value);
  }

  function sourceTag(field) {
    return sources[field] === "document" ? <span className="tag">from document</span> : null;
  }

  return (
    <form
      className="card form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="grid">
        <label className="span-2">
          <span>Full name {sourceTag("name")}</span>
          <input name="name" value={values.name} onChange={handleChange} required />
        </label>

        <label>
          <span>Monthly income (₹) {sourceTag("monthly_income")}</span>
          <input name="monthly_income" type="number" min="0" step="any" value={values.monthly_income} onChange={handleChange} required />
        </label>

        <label>
          <span>Monthly expenses (₹) {sourceTag("monthly_expenses")}</span>
          <input name="monthly_expenses" type="number" min="0" step="any" value={values.monthly_expenses} onChange={handleChange} required />
        </label>

        <label>
          <span>Monthly debt payments (₹) {sourceTag("existing_debts")}</span>
          <input name="existing_debts" type="number" min="0" step="any" value={values.existing_debts} onChange={handleChange} required />
        </label>

        <label>
          <span>Years employed {sourceTag("years_employed")}</span>
          <input name="years_employed" type="number" min="0" value={values.years_employed} onChange={handleChange} required />
        </label>

        <label>
          <span>Employment type {sourceTag("employment_type")}</span>
          <select name="employment_type" value={values.employment_type} onChange={handleChange} required>
            <option value="" disabled>Select…</option>
            {EMPLOYMENT_TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </label>

        <label>
          <span>Credit score (300–850) <span className="tag manual">enter manually</span></span>
          <input name="credit_score" type="number" min="300" max="850" value={values.credit_score} onChange={handleChange} required />
        </label>

        <label>
          <span>Loan amount (₹) <span className="tag manual">enter manually</span></span>
          <input name="loan_amount" type="number" min="1" step="any" value={values.loan_amount} onChange={handleChange} required />
        </label>

        <label>
          Prior delinquencies
          <input name="prior_delinquencies" type="number" min="0" value={values.prior_delinquencies} onChange={handleChange} />
        </label>

        <label>
          Recent credit inquiries
          <input name="recent_inquiries" type="number" min="0" value={values.recent_inquiries} onChange={handleChange} />
        </label>

        <label className="checkbox span-2">
          <input name="bankruptcy_history" type="checkbox" checked={values.bankruptcy_history} onChange={handleChange} />
          Has bankruptcy history
        </label>
      </div>

      <div className="form-actions">
        <button type="submit" className="button primary" disabled={submitting || disabled}>
          {submitting ? "Assessing…" : "Submit for assessment"}
        </button>
      </div>
    </form>
  );
}
