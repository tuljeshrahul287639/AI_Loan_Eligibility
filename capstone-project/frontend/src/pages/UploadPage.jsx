import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createApplication, fetchDocumentTypes, uploadDocument } from "../api.js";
import ApplicationForm from "../components/ApplicationForm.jsx";
import { KeyValueTable } from "../components/common.jsx";

// Fields the income documents can supply. Credit score and loan amount are always entered by hand.
const DOCUMENT_FIELDS = [
  "name",
  "monthly_income",
  "monthly_expenses",
  "existing_debts",
  "years_employed",
  "employment_type",
];

const FORM_FIELDS = [
  "name",
  "monthly_income",
  "monthly_expenses",
  "existing_debts",
  "years_employed",
  "employment_type",
  "credit_score",
  "loan_amount",
  "prior_delinquencies",
  "recent_inquiries",
  "bankruptcy_history",
];

const NUMBER_FIELDS = [
  "monthly_income",
  "monthly_expenses",
  "existing_debts",
  "years_employed",
  "credit_score",
  "loan_amount",
  "prior_delinquencies",
  "recent_inquiries",
];

const EMPTY_VALUES = {
  name: "",
  monthly_income: "",
  monthly_expenses: "",
  existing_debts: "",
  years_employed: "",
  employment_type: "",
  credit_score: "",
  loan_amount: "",
  prior_delinquencies: "0",
  recent_inquiries: "0",
  bankruptcy_history: false,
};

/** Takes the first non-empty value for each field across all uploaded documents, in upload order. */
function mergeExtracted(documents) {
  const merged = {};
  documents
    .filter((doc) => doc.extraction_status === "EXTRACTED")
    .forEach((doc) => {
      DOCUMENT_FIELDS.forEach((field) => {
        const value = doc.extracted_data?.[field];
        if (merged[field] === undefined && value !== null && value !== undefined && value !== "") {
          merged[field] = value;
        }
      });
    });
  return merged;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [docTypes, setDocTypes] = useState([]);
  const [docType, setDocType] = useState("");
  const [file, setFile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [values, setValues] = useState(EMPTY_VALUES);
  const [editedFields, setEditedFields] = useState(new Set());
  const [sources, setSources] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDocumentTypes()
      .then((types) => {
        setDocTypes(types);
        setDocType(types[0] || "");
      })
      .catch((err) => setError(`Could not load document types: ${err.message}`));
  }, []);

  // Pre-fill the form from extracted documents, but never overwrite a value the user typed.
  useEffect(() => {
    const merged = mergeExtracted(documents);
    setValues((prev) => {
      const next = { ...prev };
      Object.entries(merged).forEach(([field, value]) => {
        if (!editedFields.has(field)) next[field] = value;
      });
      return next;
    });
    setSources((prev) => {
      const next = { ...prev };
      Object.keys(merged).forEach((field) => {
        if (!editedFields.has(field)) next[field] = "document";
      });
      return next;
    });
  }, [documents, editedFields]);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const doc = await uploadDocument(file, docType);
      setDocuments((prev) => [...prev, doc]);
      setFile(null);
      document.getElementById("document-file").value = "";
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  function handleFieldChange(field, value) {
    setValues((prev) => ({ ...prev, [field]: value }));
    setEditedFields((prev) => new Set(prev).add(field));
    setSources((prev) => ({ ...prev, [field]: "manual" }));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    const payload = { ...values };
    NUMBER_FIELDS.forEach((field) => {
      payload[field] = Number(values[field]);
    });
    payload.document_ids = documents.map((doc) => doc.id);

    try {
      const created = await createApplication(payload);
      navigate(`/assessment/${created.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  const missingFields = FORM_FIELDS.filter((field) => {
    const value = values[field];
    return value === "" || value === null || value === undefined;
  });

  return (
    <div className="stack">
      <section className="card">
        <h1>Upload income documents</h1>
        <p className="muted">
          Upload a payslip, bank statement or employment letter. Gemini reads the document and fills in the
          income details below. You can check and correct every value before submitting.
        </p>
        <h3 className="sub-heading">How a document is read</h3>
        <div className="steps">
          <div className="step">
            <div className="step-icon">📄</div>
            <div className="step-number">Step 1</div>
            <strong>Upload</strong>
            <p>Add payslips, bank statements or employment letters.</p>
          </div>
          <div className="step">
            <div className="step-icon">✨</div>
            <div className="step-number">Step 2</div>
            <strong>Extract</strong>
            <p>Gemini reads each document and fills in the income details.</p>
          </div>
        </div>

        <div className="upload-row">
          <label>
            Document type
            <select value={docType} onChange={(event) => setDocType(event.target.value)} disabled={uploading}>
              {docTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </label>
          <label className="grow">
            File (PDF, PNG, JPG, TXT or CSV, max 10 MB)
            <input
              id="document-file"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt,.csv"
              onChange={(event) => setFile(event.target.files[0] || null)}
              disabled={uploading}
            />
          </label>
          <button type="button" className="button primary" onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? "Extracting…" : "Upload and extract"}
          </button>
        </div>

        {error && <div className="alert">{error}</div>}
      </section>

      {documents.length > 0 && (
        <section className="card">
          <h2>Uploaded documents</h2>
          {documents.map((doc) => (
            <div key={doc.id} className="document-block">
              <div className="section-header">
                <strong>{doc.doc_type}</strong>
                <span className="muted small">{doc.original_filename}</span>
                <span className={doc.extraction_status === "EXTRACTED" ? "badge approve" : "badge reject"}>
                  {doc.extraction_status === "EXTRACTED" ? "Extracted" : "Extraction failed"}
                </span>
              </div>
              {doc.extraction_status === "EXTRACTED" ? (
                <KeyValueTable data={doc.extracted_data} />
              ) : (
                <div className="alert">
                  {doc.extraction_error}. You can still fill in the form manually.
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      <section className="stack">
        <div className="section-header">
          <h2>Applicant details</h2>
          <span className="muted small">
            {missingFields.length === 0
              ? "All required fields are filled"
              : `${missingFields.length} required field(s) still empty`}
          </span>
        </div>
        <ApplicationForm
          values={values}
          sources={sources}
          onChange={handleFieldChange}
          onSubmit={handleSubmit}
          submitting={submitting}
          disabled={missingFields.length > 0}
        />
      </section>
    </div>
  );
}
