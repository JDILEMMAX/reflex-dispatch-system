/**
 * auth.js - Auth state management for the Reflex Delivery System.
 * Handles session persistence in localStorage and auth header generation.
 * Imports only from ui.js to remain free of circular dependencies.
 */

const SESSION_KEY = "reflex_session";

// In-memory auth state. Private to this module.
let _auth = null;

// ---------- State accessors ----------

/** Returns the current auth object { token, user } or null. */
export function getAuth() {
  return _auth;
}

/**
 * Set the active auth state and persist to localStorage.
 * Pass null to clear the session.
 * @param {Object|null} auth
 */
export function setAuth(auth) {
  _auth = auth;
  if (auth) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(auth));
  } else {
    localStorage.removeItem(SESSION_KEY);
  }
}

/**
 * Attempt to rehydrate auth from localStorage.
 * Returns the parsed auth object if valid, or null.
 * @returns {Object|null}
 */
export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.token && parsed.user) return parsed;
    return null;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

/**
 * Build the JSON + Bearer auth headers from the current in-memory token.
 * Safe to call when logged out (returns headers without Authorization).
 * @returns {Object}
 */
export function getAuthHeaders() {
  if (!_auth || !_auth.token) return { "Content-Type": "application/json" };
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${_auth.token}`,
  };
}
