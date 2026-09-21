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
