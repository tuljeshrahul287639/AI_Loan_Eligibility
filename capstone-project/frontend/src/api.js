const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const SESSION_KEY = "loan_session";

// The login session (token, username, role) is kept in sessionStorage so it ends when the browser tab closes.
export function getSession() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY)) || null;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("session-changed"));
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("session-changed"));
}

async function request(path, options = {}) {
  const session = getSession();
  const headers = { ...(options.headers || {}) };
  if (session) headers.Authorization = `Bearer ${session.token}`;

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((d) => `${d.loc.slice(-1)[0]}: ${d.msg}`).join("; ");
      }
    } catch {
      // Response body was not JSON; keep the generic message.
    }
    if (response.status === 401 && session) {
      clearSession();
    }
    throw new Error(message);
  }

  return response.json();
}

function postJson(path, payload) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function storeSessionFrom(login) {
  saveSession({ token: login.token, username: login.username, full_name: login.full_name, role: login.role });
  return login;
}

export function signup(payload) {
  return postJson("/api/auth/signup", payload).then(storeSessionFrom);
}

export function userLogin(payload) {
  return postJson("/api/auth/user/login", payload).then(storeSessionFrom);
}

export function adminLogin(payload) {
  return postJson("/api/auth/admin/login", payload).then(storeSessionFrom);
}

export async function logout() {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } finally {
    clearSession();
  }
}

export function fetchDocumentTypes() {
  return request("/api/documents/types");
}

export function uploadDocument(file, docType) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);
  return request("/api/documents/extract", { method: "POST", body: formData });
}

export function createApplication(payload) {
  return postJson("/api/applications", payload);
}

export function fetchApplications({ status, limit } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  const query = params.toString() ? `?${params}` : "";
  return request(`/api/applications${query}`);
}

export function fetchApplication(id) {
  return request(`/api/applications/${id}`);
}

export function reviewApplication(id, { decision, note }) {
  return postJson(`/api/applications/${id}/review`, { decision, note });
}

export function fetchStats() {
  return request("/api/applications/stats");
}

export function importSamples(limit = 10) {
  return request(`/api/applications/import-samples?limit=${limit}`, { method: "POST" });
}
