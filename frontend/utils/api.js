/**
 * api.js - All backend HTTP calls for the Reflex Delivery System.
 * Each function is a thin async wrapper returning parsed JSON or throwing an Error.
 * Auth headers are passed as parameters - this module holds no auth state.
 */

const API_BASE = window.location.origin;

/**
 * POST /api/auth/login
 * @returns {Object} { token, user }
 */
export async function apiLogin(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Authentication failed. Check credentials.");
  }
  return res.json();
}

/**
 * GET /api/orders/retailer - Retailer's own order list
 * @param {Object} authHeaders
 */
export async function apiFetchOrders(authHeaders) {
  const res = await fetch(`${API_BASE}/api/orders/retailer`, { headers: authHeaders });
  if (!res.ok) throw new Error("Failed to load retailer orders");
  return res.json();
}

/**
 * POST /api/orders - Create a new delivery request
 * @param {Object} payload
 * @param {Object} authHeaders
 */
export async function apiCreateOrder(payload, authHeaders) {
  const res = await fetch(`${API_BASE}/api/orders`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to log delivery request");
  }
  return res.json();
}

/**
 * GET /api/dispatch/orders - Full order queue for the dispatcher
 * @param {Object} authHeaders
 */
export async function apiFetchDispatchOrders(authHeaders) {
  const res = await fetch(`${API_BASE}/api/dispatch/orders`, { headers: authHeaders });
  if (!res.ok) throw new Error("Failed to load dispatch queue");
  return res.json();
}

/**
 * GET /api/dispatch/riders - Active rider roster
 * @param {Object} authHeaders
 */
export async function apiFetchRiders(authHeaders) {
  const res = await fetch(`${API_BASE}/api/dispatch/riders`, { headers: authHeaders });
  if (!res.ok) throw new Error("Failed to load rider roster");
  return res.json();
}

/**
 * POST /api/dispatch/assign - Assign a rider to an order
 * @param {number} orderId
 * @param {number} riderId
 * @param {Object} authHeaders
 */
export async function apiAssignRider(orderId, riderId, authHeaders) {
  const res = await fetch(`${API_BASE}/api/dispatch/assign`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({ order_id: orderId, rider_id: riderId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Rider assignment failed");
  }
  return res.json();
}

/**
 * GET /api/rider/tasks - Rider's active delivery queue
 * @param {Object} authHeaders
 */
export async function apiFetchRiderTasks(authHeaders) {
  const res = await fetch(`${API_BASE}/api/rider/tasks`, { headers: authHeaders });
  if (!res.ok) throw new Error("Failed to load rider task queue");
  return res.json();
}

/**
 * POST /api/rider/milestone - Push a delivery milestone update
 * @param {Object} payload - { order_id, new_status, doorstep_pin? }
 * @param {Object} authHeaders
 */
export async function apiUpdateMilestone(payload, authHeaders) {
  const res = await fetch(`${API_BASE}/api/rider/milestone`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Milestone update failed");
  }
  return res.json();
}

/**
 * POST /api/orders/{id}/cancel - Cancel a pending order
 * @param {number} orderId
 * @param {string} reason
 * @param {Object} authHeaders
 */
export async function apiCancelOrder(orderId, reason, authHeaders) {
  const res = await fetch(`${API_BASE}/api/orders/${orderId}/cancel`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Cancellation failed");
  }
  return res.json();
}

/**
 * POST /api/dispatch/reassign - Reassign a delivery to a different rider
 * @param {number} orderId
 * @param {number} newRiderId
 * @param {string} reason
 * @param {Object} authHeaders
 */
export async function apiReassignOrder(orderId, newRiderId, reason, authHeaders) {
  const res = await fetch(`${API_BASE}/api/dispatch/reassign`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({ order_id: orderId, new_rider_id: newRiderId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Reassignment failed");
  }
  return res.json();
}
