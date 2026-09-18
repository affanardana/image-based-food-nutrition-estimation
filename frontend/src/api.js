// In development, Vite proxies /api to the local backend (see
// vite.config.js), so no origin is needed. In a deployment the backend
// lives on another origin, configured with VITE_API_BASE_URL — e.g.
// https://ifne-api.onrender.com — and CORS_ORIGINS on the backend must
// include this site's origin.
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(
  /\/$/,
  ""
);

const BASE_URL = `${API_ORIGIN}/api/v1`;

// A request slower than this is almost certainly a cold start: the free
// backend tier spins down when idle, and the vision container scales
// down too. Long enough not to fire on ordinary slow requests, short
// enough to appear well before a boot finishes.
const SLOW_REQUEST_MS = 6000;

const slowRequestListeners = new Set();
let slowRequests = 0;

/**
 * Subscribe to "a request is taking unusually long" changes.
 * Returns an unsubscribe function, so it can be used directly as a
 * `useEffect` cleanup.
 */
export function onSlowRequestsChange(listener) {
  slowRequestListeners.add(listener);
  listener(slowRequests > 0);
  return () => slowRequestListeners.delete(listener);
}

function notifySlowRequests() {
  for (const listener of slowRequestListeners) {
    listener(slowRequests > 0);
  }
}

/**
 * Absolute URL for an image path returned by the API.
 *
 * The backend reports image and crop locations as paths
 * (/api/v1/images/...), which only resolve correctly when the frontend
 * and backend share an origin. Prefixing the configured API origin makes
 * them work when the two are deployed separately.
 */
export function assetUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_ORIGIN}${path}`;
}

/**
 * Perform an API request and unwrap the {status, data} envelope.
 * Throws an Error with a `code` property on failure.
 */
async function request(path, options = {}) {
  let slow = false;
  const timer = setTimeout(() => {
    slow = true;
    slowRequests += 1;
    notifySlowRequests();
  }, SLOW_REQUEST_MS);

  try {
    const response = await fetch(`${BASE_URL}${path}`, options);
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(
        body?.error?.message ?? `Request failed (${response.status})`
      );
      error.code = body?.error?.code ?? "INTERNAL_ERROR";
      throw error;
    }
    return body.data;
  } finally {
    clearTimeout(timer);
    if (slow) {
      slowRequests -= 1;
      notifySlowRequests();
    }
  }
}

export function analyzeMeal(file, suggestLabels = false) {
  const form = new FormData();
  form.append("image", file);
  form.append("suggest_labels", suggestLabels ? "true" : "false");
  return request("/meals/analyze", { method: "POST", body: form });
}

export function labelMeal(mealId, assignments, name = null) {
  return request(`/meals/${mealId}/label`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignments, name }),
  });
}

export function replaceLabels(mealId, assignments, name = null) {
  return request(`/meals/${mealId}/labels`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignments, name }),
  });
}

export function updateMeal(mealId, corrections) {
  return request(`/meals/${mealId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ food_items: corrections }),
  });
}

export function renameMeal(mealId, name) {
  return request(`/meals/${mealId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function discardSegments(mealId, segmentIds) {
  return request(`/meals/${mealId}/segments/discard`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment_ids: segmentIds }),
  });
}

export function deleteMeal(mealId) {
  return request(`/meals/${mealId}`, { method: "DELETE" });
}

export function getMeal(mealId) {
  return request(`/meals/${mealId}`);
}

export function listMeals(limit = 20, offset = 0) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/meals?${params.toString()}`);
}

export function searchFoods(query, limit = 20) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return request(`/foods/search?${params.toString()}`);
}
