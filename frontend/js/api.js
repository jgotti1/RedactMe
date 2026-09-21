const apiBase = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

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
export const scanPdf = (id, token, useAi = true, signal) => documentRequest(id, token, { method: 'POST', signal }, `/scan?use_ai=${useAi}`);
export const getPdfStatus = (id, token) => documentRequest(id, token, { signal: AbortSignal.timeout(10000) });
