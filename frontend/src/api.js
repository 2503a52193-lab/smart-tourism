const API_URL = import.meta.env.VITE_API_URL || "/api";

export function token() {
  return localStorage.getItem("tourism_token");
}

export async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return response;
}

export async function json(path, options) {
  const response = await api(path, options);
  return response.json();
}
