// Production is same-origin (relative /api paths); local dev defaults to the separate backend server.
const apiBase = (import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");

export async function getGreeting(user, signal) {
  const token = await user.getIdToken();
  const response = await fetch(`${apiBase}/api/hello`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "The backend request failed.");
  }
  if (typeof payload.message !== "string") throw new Error("Unexpected backend response.");
  return payload.message;
}

async function documentRequest(id, token, options = {}, suffix = '') {
  const response = await fetch(`${apiBase}/api/documents/${encodeURIComponent(id)}${suffix}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/pdf' } : {}) },
    cache: 'no-store',
  });
  if (response.status === 204) return;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'The PDF request failed. Please try again.');
  return payload;
}
export const uploadPdf = (id, file, token, signal) => documentRequest(id, token, { method: 'POST', body: file, signal });
export const discardPdf = (id, token, keepalive = false) => documentRequest(id, token, { method: 'DELETE', keepalive, signal: AbortSignal.timeout(10000) });
export const scanPdf = async (id, token, terms = [], sensitivity = 'balanced', signal) => (await binaryRequest(`/api/documents/${encodeURIComponent(id)}/scan`, token, { method: 'POST', json: { terms, sensitivity }, signal })).json();
export const getPdfStatus = (id, token) => documentRequest(id, token, { signal: AbortSignal.timeout(10000) });

async function binaryRequest(path, token, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: { Authorization: `Bearer ${token}`, ...(options.json ? { 'Content-Type': 'application/json' } : {}) }, body: options.json ? JSON.stringify(options.json) : undefined, cache: 'no-store' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(typeof payload.detail === 'string' ? payload.detail : 'The request failed. Please try again.');
    error.code = payload.code;
    error.warningToken = payload.warning_token;
    error.page = payload.page;
    error.category = payload.category;
    throw error;
  }
  return response;
}
export const previewPage = async (id, page, token, signal) => (await binaryRequest(`/api/documents/${encodeURIComponent(id)}/pages/${page}/preview`, token, { signal })).blob();
export const redactPdf = async (id, body, token) => (await binaryRequest(`/api/documents/${encodeURIComponent(id)}/redact`, token, { method: 'POST', json: body, signal: AbortSignal.timeout(320000) })).json();
export const downloadPdf = async (id, token) => (await binaryRequest(`/api/documents/${encodeURIComponent(id)}/download`, token, { signal: AbortSignal.timeout(60000) })).blob();
