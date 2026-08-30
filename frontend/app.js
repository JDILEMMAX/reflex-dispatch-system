/**
 * app.js - Reflex Delivery System: Central ES6 Module Entry Point
 *
 * Imports utility modules and owns all application logic:
 * persona switching, render functions, event wiring and polling.
 *
 * All functions invoked by inline HTML onclick handlers are explicitly
 * attached to window at the bottom of this file.
 */

import { showToast, escapeHtml, formatDate } from "./utils/ui.js";
import { getAuth, setAuth, getStoredAuth, getAuthHeaders } from "./utils/auth.js";
import { startPolling, stopPolling } from "./utils/polling.js";

const QR_CODE_API = "https://api.qrserver.com/v1/create-qr-code/";

// Application state
let activeRoleView = "ROLE_RETAILER";
let activePodOrderId = null;
let activePodToken = null;
let currentPinInput = "";
let allRiders = [];
let activeDispatchQueue = "UNASSIGNED";

// ==================================================
// Initialization & Theme Lifecycle
// ==================================================

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initEventListeners();
  checkStoredSession();
});

function initTheme() {
  const savedTheme = localStorage.getItem("reflex_theme") || "light";
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("reflex_theme", theme);

  const sunIcon = document.getElementById("themeIconSun");
  const moonIcon = document.getElementById("themeIconMoon");
  const toggleText = document.getElementById("themeToggleText");

  if (theme === "dark") {
    if (sunIcon) sunIcon.style.display = "inline-block";
    if (moonIcon) moonIcon.style.display = "none";
    if (toggleText) toggleText.textContent = "Light Mode";
  } else {
    if (sunIcon) sunIcon.style.display = "none";
    if (moonIcon) moonIcon.style.display = "inline-block";
    if (toggleText) toggleText.textContent = "Dark Mode";
  }
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  applyTheme(newTheme);
}

function checkStoredSession() {
  const stored = getStoredAuth();
  if (stored) {
    setAuth(stored);
    applyAuthenticatedState();
  } else {
    showLoginView();
  }
}

function initEventListeners() {
  const loginForm = document.getElementById("loginForm");
  if (loginForm) loginForm.addEventListener("submit", handleLoginSubmit);

  const createOrderForm = document.getElementById("createOrderForm");
  if (createOrderForm) createOrderForm.addEventListener("submit", handleCreateOrderSubmit);
}

// ==================================================
// Authentication
// ==================================================

async function handleLoginSubmit(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("loginUsername");
  const passwordInput = document.getElementById("loginPassword");
  const errorAlert = document.getElementById("loginErrorAlert");

  if (errorAlert) errorAlert.style.display = "none";

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showLoginError("Please enter both username and password");
    return;
  }

  try {
    const res = await fetch(`${window.location.origin}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Authentication failed. Check credentials.");
    }

    const data = await res.json();
    // Build user from flat response fields (no nested data.user)
    const user = {
      id: data.user_id,
      username: data.username,
      full_name: data.full_name,
      role: data.role,
      rider_id: data.rider_id,
    };
    setAuth({ token: data.access_token, user });
    applyAuthenticatedState();
    showToast(`Welcome back, ${user.full_name}`, "success");
  } catch (err) {
    showLoginError(err.message);
  }
}

function showLoginError(msg) {
  const el = document.getElementById("loginErrorAlert");
  if (!el) return;
  el.textContent = msg;
  el.style.display = "block";
}

async function quickLogin(username, password) {
  // Authenticate directly and build session - avoids form dispatch timing issues
  try {
    const res = await fetch(`${window.location.origin}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Authentication failed. Check credentials.");
    }
    const data = await res.json();
    const user = {
      id: data.user_id,
      username: data.username,
      full_name: data.full_name,
      role: data.role,
      rider_id: data.rider_id,
    };
    setAuth({ token: data.access_token, user });
    applyAuthenticatedState();
    showToast(`Welcome back, ${user.full_name}`, "success");
  } catch (err) {
    showLoginError(err.message);
  }
}

function logout() {
  stopPolling();
  setAuth(null);
  showLoginView();
  showToast("Logged out successfully", "info");
}

function applyAuthenticatedState() {
  document.getElementById("viewLogin").classList.remove("active");

  const personaNav = document.getElementById("personaSwitcherNav");
  if (personaNav) personaNav.style.display = "flex";

  const demoSwitcher = document.getElementById("demoSwitcher");
  if (demoSwitcher) demoSwitcher.style.display = "none";

  const auth = getAuth();
  const user = auth.user;

  const nameEl = document.getElementById("activeUserName");
  if (nameEl) nameEl.textContent = user.full_name;

  const roleEl = document.getElementById("activeUserRole");
  if (roleEl) roleEl.textContent = user.role.replace("ROLE_", "");

  const navStorePortalBtn = document.getElementById("navStorePortalBtn");
  const navDispatchBtn = document.getElementById("navDispatchBtn");
  const navRiderBtn = document.getElementById("navRiderBtn");

  if (navStorePortalBtn) navStorePortalBtn.style.display = user.role === 'ROLE_RETAILER' ? 'block' : 'none';
  if (navDispatchBtn) navDispatchBtn.style.display = user.role === 'ROLE_DISPATCHER' ? 'block' : 'none';
  if (navRiderBtn) navRiderBtn.style.display = user.role === 'ROLE_RIDER' ? 'block' : 'none';

  document.querySelectorAll(".persona-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.dataset.role === user.role) btn.classList.add("active");
  });

  switchPersonaView(user.role);
  startPolling(livePollingTick, 3000);
}

function showLoginView() {
  stopPolling();
  const personaNav = document.getElementById("personaSwitcherNav");
  if (personaNav) personaNav.style.display = "none";

  const demoSwitcher = document.getElementById("demoSwitcher");
  if (demoSwitcher) demoSwitcher.style.display = "flex";

  document.querySelectorAll(".view-section").forEach((s) => s.classList.remove("active"));
  document.getElementById("viewLogin").classList.add("active");
}

function switchPersonaView(role) {
  const auth = getAuth();
  if (!auth || auth.user.role !== role) {
    showToast("Access restricted to assigned role. Use Demo Role Switch to change credentials.", "error");
    return;
  }

  activeRoleView = role;
  document.querySelectorAll(".view-section").forEach((s) => s.classList.remove("active"));

  document.querySelectorAll(".persona-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.role === role);
  });

  if (role === "ROLE_RETAILER") {
    document.getElementById("viewRetailer").classList.add("active");
    loadRetailerDashboard();
  } else if (role === "ROLE_DISPATCHER") {
    document.getElementById("viewDispatcher").classList.add("active");
    loadDispatcherDashboard();
  } else if (role === "ROLE_RIDER") {
    document.getElementById("viewRider").classList.add("active");
    loadRiderTasks();
  }
}

// ==================================================
// Live Polling Engine
// ==================================================

function livePollingTick() {
  const auth = getAuth();
  if (!auth) return;

  if (auth.user.role === "ROLE_RETAILER") {
    loadRetailerDashboard(true);
  } else if (auth.user.role === "ROLE_DISPATCHER") {
    // Skip rebuild if a rider dropdown is focused to avoid losing the user's selection
    const activeEl = document.activeElement;
    if (activeEl && activeEl.tagName === "SELECT" && activeEl.id.startsWith("assign_select_")) return;
    loadDispatcherDashboard(true);
  } else if (auth.user.role === "ROLE_RIDER") {
    loadRiderTasks(true);
  }
}

// ==================================================
// Retailer Dashboard
// ==================================================

async function loadRetailerDashboard(isSilent = false) {
  try {
    // /api/orders GET is POST-only (201 Created); retailer list lives at /api/orders/retailer
    const res = await fetch(`${window.location.origin}/api/orders/retailer`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load retailer orders");
    const orders = await res.json();
    renderRetailerOrdersTable(orders);
    updateRetailerStats(orders);
  } catch (err) {
    if (!isSilent) showToast(err.message, "error");
  }
}

function updateRetailerStats(orders) {
  const activeCount = orders.filter((o) => o.status !== "DELIVERED").length;
  const completedCount = orders.filter((o) => o.status === "DELIVERED").length;
  const transitCount = orders.filter((o) => ["PICKED_UP", "ARRIVED"].includes(o.status)).length;

  const statActive = document.getElementById("statRetailerActive");
  const statCompleted = document.getElementById("statRetailerCompleted");
  const statTransit = document.getElementById("statRetailerTransit");

  if (statActive) statActive.textContent = activeCount;
  if (statCompleted) statCompleted.textContent = completedCount;
  if (statTransit) statTransit.textContent = transitCount;
}

function renderRetailerOrdersTable(orders) {
  const tbody = document.getElementById("retailerOrdersBody");
  if (!tbody) return;

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No delivery orders logged yet. Click '+ Log New Delivery Request' to start.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map((o) => `
    <tr>
      <td>
        <span class="token-pill">${o.tracking_token}</span><br>
        <small style="color: var(--text-muted);">${formatDate(o.created_at)}</small>
      </td>
      <td>
        <strong>${escapeHtml(o.customer_name)}</strong><br>
        <small style="color: var(--accent-cyan);">${escapeHtml(o.customer_phone)}</small>
      </td>
      <td><span style="font-size: 0.85rem;">${escapeHtml(o.delivery_address)}</span></td>
      <td>
        <strong>${escapeHtml(o.item_description)}</strong><br>
        <small style="color: var(--text-muted);">Val: KES ${Number(o.package_value).toLocaleString()}</small>
      </td>
      <td><strong style="color: var(--accent-green);">KES ${Number(o.delivery_fee).toLocaleString()}</strong></td>
      <td><span class="status-badge status-${o.status}">${o.status.replace(/_/g, " ")}</span></td>
      <td><span class="pin-tag">PIN: ${escapeHtml(o.verification_pin)}</span></td>
      <td style="text-align: center;">
        <div class="qr-code-container">
          <img
            src="${QR_CODE_API}?size=100x100&data=${encodeURIComponent(o.tracking_token)}"
            alt="QR Code for ${escapeHtml(o.tracking_token)}"
            width="100" height="100"
            style="background: white; padding: 5px; border-radius: 6px;"
          >
          <br><small style="color: var(--text-muted);">Scan to track</small>
        </div>
      </td>
      <td>
        ${o.rider_name
          ? `<span style="display:flex;align-items:center;gap:0.4rem;">${svgRider(16)} ${escapeHtml(o.rider_name)}</span><br><small style="color: var(--text-muted);">${escapeHtml(o.vehicle_plate || "")}</small>`
          : `<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>`
        }
      </td>
      <td style="min-width: 130px; text-align: center;">
        <a href="/track/${o.tracking_token}" target="_blank" class="action-btn">
          Track Order ↗
        </a>
      </td>
    </tr>
  `).join("");
}

function openCreateOrderModal() {
  const modal = document.getElementById("modalCreateOrder");
  if (modal) modal.classList.add("active");
  const firstInput = document.getElementById("orderCustomerName");
  if (firstInput) firstInput.focus();
}

function closeCreateOrderModal() {
  const modal = document.getElementById("modalCreateOrder");
  if (modal) modal.classList.remove("active");
  const form = document.getElementById("createOrderForm");
  if (form) form.reset();
}

async function handleCreateOrderSubmit(e) {
  e.preventDefault();
  const payload = {
    customer_name: document.getElementById("orderCustomerName").value.trim(),
    customer_phone: document.getElementById("orderCustomerPhone").value.trim(),
    delivery_address: document.getElementById("orderAddress").value.trim(),
    item_description: document.getElementById("orderItemDesc").value.trim(),
    package_value: parseFloat(document.getElementById("orderValue").value),
    delivery_fee: parseFloat(document.getElementById("orderFee").value),
  };

  try {
    const res = await fetch(`${window.location.origin}/api/orders`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to log delivery request");
    }

    const created = await res.json();
    closeCreateOrderModal();
    showToast(`Order logged! Token: ${created.tracking_token} | PIN: ${created.verification_pin}`, "success");
    loadRetailerDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==================================================
// Dispatcher Command Board
// ==================================================

async function loadDispatcherDashboard(isSilent = false) {
  try {
    const origin = window.location.origin;
    const [ordersRes, ridersRes] = await Promise.all([
      fetch(`${origin}/api/dispatch/orders`, { headers: getAuthHeaders() }),
      fetch(`${origin}/api/dispatch/riders`, { headers: getAuthHeaders() }),
    ]);

    if (!ordersRes.ok || !ridersRes.ok) throw new Error("Failed to load dispatch board data");

    const orders = await ordersRes.json();
    allRiders = await ridersRes.json();

    renderDispatcherOrdersTable(orders);
    renderRiderRoster();
    updateDispatcherMetrics(orders);
  } catch (err) {
    if (!isSilent) showToast(err.message, "error");
  }
}

function updateDispatcherMetrics(orders) {
  const unassigned = orders.filter((o) => o.status === "ORDER_LOGGED").length;
  const inTransit = orders.filter((o) => ["ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status)).length;
  const delivered = orders.filter((o) => o.status === "DELIVERED").length;

  const elUnassigned = document.getElementById("metricUnassigned");
  const elInTransit = document.getElementById("metricInTransit");
  const elDelivered = document.getElementById("metricDelivered");
  const elActiveRiders = document.getElementById("metricActiveRiders");

  if (elUnassigned) elUnassigned.textContent = unassigned;
  if (elInTransit) elInTransit.textContent = inTransit;
  if (elDelivered) elDelivered.textContent = delivered;
  if (elActiveRiders) elActiveRiders.textContent = allRiders.length;
}

function switchDispatchQueue(queueStatus) {
  activeDispatchQueue = queueStatus;

  // Update active tab styling
  ["UNASSIGNED", "IN_TRANSIT", "DELIVERED"].forEach((q) => {
    const tabId = q === "UNASSIGNED" ? "tabUnassigned" : q === "IN_TRANSIT" ? "tabInTransit" : "tabDelivered";
    const tab = document.getElementById(tabId);
    if (tab) tab.classList.toggle("active", q === queueStatus);
  });

  loadDispatcherDashboard();
}

function renderDispatcherOrdersTable(orders) {
  const tbody = document.getElementById("dispatcherOrdersBody");
  if (!tbody) return;

  // Filter by active queue tab
  let filtered = orders;
  if (activeDispatchQueue === "UNASSIGNED") {
    filtered = orders.filter((o) => o.status === "ORDER_LOGGED");
  } else if (activeDispatchQueue === "IN_TRANSIT") {
    filtered = orders.filter((o) => ["ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status));
  } else if (activeDispatchQueue === "DELIVERED") {
    filtered = orders.filter((o) => o.status === "DELIVERED");
  }

  // Update tab counts
  const countUnassigned = document.getElementById("countUnassigned");
  const countInTransit = document.getElementById("countInTransit");
  const countDelivered = document.getElementById("countDelivered");
  if (countUnassigned) countUnassigned.textContent = orders.filter((o) => o.status === "ORDER_LOGGED").length;
  if (countInTransit) countInTransit.textContent = orders.filter((o) => ["ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status)).length;
  if (countDelivered) countDelivered.textContent = orders.filter((o) => o.status === "DELIVERED").length;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No orders in this queue.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((o) => `
    <tr>
      <td><span class="token-pill">${o.tracking_token}</span></td>
      <td>
        <strong>${escapeHtml(o.retailer_name || "Merchant")}</strong><br>
        <small style="color: var(--text-muted);">${escapeHtml(o.retailer_phone || "")}</small>
      </td>
      <td>
        <strong>${escapeHtml(o.customer_name)}</strong><br>
        <small style="color: var(--accent-cyan);">${escapeHtml(o.customer_phone)}</small><br>
        <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(o.delivery_address)}</span>
      </td>
      <td>
        <span>${escapeHtml(o.item_description)}</span><br>
        <small style="color: var(--accent-green);">Fee: KES ${Number(o.delivery_fee).toLocaleString()}</small>
      </td>
      <td><span class="status-badge status-${o.status}">${o.status.replace(/_/g, " ")}</span></td>
      <td><span class="pin-tag">PIN: ${o.verification_pin}</span></td>
      <td>
        ${o.rider_name
          ? `<span style="display:flex;align-items:center;gap:0.4rem;">${svgRider(16)} ${escapeHtml(o.rider_name)}</span><br><small style="color: var(--text-muted);">${escapeHtml(o.vehicle_plate || "")}</small>`
          : `<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>`
        }
      </td>
      <td style="min-width: 130px; text-align: center;">
        ${o.status === "ORDER_LOGGED" ? `
          <div style="display: flex; gap: 0.4rem; align-items: center; justify-content: center;">
            <select id="assign_select_${o.id}" class="form-input" style="padding: 0.35rem 0.5rem; font-size: 0.8rem; width: 140px;">
              <option value="">Select Rider...</option>
              ${allRiders.map((r) => `<option value="${r.id}">${escapeHtml(r.full_name)} (${escapeHtml(r.vehicle_plate)})</option>`).join("")}
            </select>
            <button class="btn-primary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;" onclick="assignOrderToRider(${o.id})">
              Assign
            </button>
          </div>
        ` : `
          <a href="/track/${o.tracking_token}" target="_blank" class="action-btn">
            Live Stepper ↗
          </a>
        `}
      </td>
    </tr>
  `).join("");
}

async function assignOrderToRider(orderId) {
  const selectEl = document.getElementById(`assign_select_${orderId}`);
  if (!selectEl || !selectEl.value) {
    showToast("Please choose an active rider from the dropdown roster", "error");
    return;
  }

  const riderId = parseInt(selectEl.value, 10);
  try {
    const res = await fetch(`${window.location.origin}/api/dispatch/assign`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ order_id: orderId, rider_id: riderId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Assignment failed");
    }
    showToast("Order assigned to rider successfully", "success");
    loadDispatcherDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderRiderRoster() {
  const container = document.getElementById("riderRosterContainer");
  if (!container) return;

  if (allRiders.length === 0) {
    container.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:2rem;font-size:0.85rem;">No active riders online.</div>`;
    return;
  }

  container.innerHTML = allRiders.map((r) => `
    <div class="rider-card">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div class="rider-avatar">${svgRider(20)}</div>
        <div>
          <strong style="font-size: 0.9rem;">${escapeHtml(r.full_name)}</strong><br>
          <small style="color: var(--text-muted);">${escapeHtml(r.vehicle_plate)} &bull; ${escapeHtml(r.phone_number)}</small>
        </div>
      </div>
      <div style="text-align: right;">
        <span class="status-badge ${r.active_tasks_count > 0 ? "status-PICKED_UP" : "status-ARRIVED"}" style="font-size: 0.7rem;">
          ${r.active_tasks_count} Active
        </span>
      </div>
    </div>
  `).join("");
}

// ==================================================
// Rider Mobile Terminal
// ==================================================

async function loadRiderTasks(isSilent = false) {
  try {
    const res = await fetch(`${window.location.origin}/api/rider/tasks`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load rider assignments");
    const tasks = await res.json();
    renderRiderTaskCards(tasks);
  } catch (err) {
    if (!isSilent) showToast(err.message, "error");
  }
}

function renderRiderTaskCards(tasks) {
  const container = document.getElementById("riderTasksContainer");
  if (!container) return;

  if (tasks.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <div style="display:flex;justify-content:center;margin-bottom:0.75rem;opacity:0.5;">${svgRider(40)}</div>
        <h3>No Assigned Runs</h3>
        <p style="font-size: 0.85rem; margin-top: 0.25rem;">New dispatch runs from central control will appear here in real-time.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = tasks.map((t) => {
    let cardClass = "";
    if (t.status === "PICKED_UP") cardClass = "in-transit";
    if (t.status === "ARRIVED") cardClass = "arrived";

    return `
      <div class="task-card ${cardClass}">
        <div class="task-header">
          <div><span class="token-pill">${t.tracking_token}</span></div>
          <span class="status-badge status-${t.status}">${t.status.replace(/_/g, " ")}</span>
        </div>

        <div class="task-detail-row">
          <div class="task-detail-label">Pickup Shop:</div>
          <div class="task-detail-value">
            <strong>${escapeHtml(t.retailer_name || "Merchant")}</strong> (${escapeHtml(t.retailer_phone || "")})
          </div>
        </div>

        <div class="task-detail-row">
          <div class="task-detail-label">Deliver To:</div>
          <div class="task-detail-value">
            <strong>${escapeHtml(t.customer_name)}</strong><br>
            <span>${escapeHtml(t.delivery_address)}</span><br>
            <small style="color: var(--accent-cyan);">${escapeHtml(t.customer_phone)}</small>
          </div>
        </div>

        <div class="task-detail-row">
          <div class="task-detail-label">Package:</div>
          <div class="task-detail-value">
            ${escapeHtml(t.item_description)} &bull; <strong style="color: var(--accent-green);">Fee: KES ${Number(t.delivery_fee).toLocaleString()}</strong>
          </div>
        </div>

        <div class="task-actions">
          ${t.status === "ASSIGNED" ? `
            <button class="btn-milestone btn-milestone-pickup" onclick="triggerRiderMilestone(${t.id}, 'PICKED_UP')">
              ${svgPackage(18)} Confirm Shop Package Pickup
            </button>
          ` : ""}

          ${t.status === "PICKED_UP" ? `
            <button class="btn-milestone btn-milestone-arrived" onclick="triggerRiderMilestone(${t.id}, 'ARRIVED')">
              ${svgPin(18)} Confirm Arrival at Customer Doorstep
            </button>
          ` : ""}

          ${t.status === "ARRIVED" ? `
            <button class="btn-milestone btn-milestone-pod" onclick="openPodModal(${t.id}, '${t.tracking_token}')">
              ${svgLock(18)} Enter Customer PIN / Scan POD
            </button>
          ` : ""}

          ${t.status === "DELIVERED" ? `
            <div style="text-align: center; color: var(--accent-green); font-weight: 700; font-size: 0.9rem; padding: 0.5rem; background: rgba(0, 230, 118, 0.1); border-radius: var(--radius-sm); border: 1px solid var(--accent-green);">
              ${svgCheckCircle(18)} Delivery Verified &amp; Chain of Custody Closed
            </div>
          ` : ""}
        </div>
      </div>
    `;
  }).join("");
}

async function triggerRiderMilestone(orderId, newStatus) {
  try {
    const res = await fetch(`${window.location.origin}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ order_id: orderId, new_status: newStatus }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Milestone update failed");
    }
    showToast(`Status updated to ${newStatus.replace(/_/g, " ")}`, "success");
    loadRiderTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==================================================
// Dual-Factor Proof of Delivery (POD) Keypad
// ==================================================

function openPodModal(orderId, token) {
  activePodOrderId = orderId;
  activePodToken = token;
  currentPinInput = "";
  const tokenEl = document.getElementById("podOrderToken");
  if (tokenEl) tokenEl.textContent = token;
  updatePinDisplay();
  const modal = document.getElementById("modalPodKeypad");
  if (modal) modal.classList.add("active");
}

function closePodModal() {
  const modal = document.getElementById("modalPodKeypad");
  if (modal) modal.classList.remove("active");
  activePodOrderId = null;
  activePodToken = null;
  currentPinInput = "";
}

function appendPinDigit(digit) {
  if (currentPinInput.length < 4) {
    currentPinInput += digit;
    updatePinDisplay();
  }
}

function backspacePinDigit() {
  currentPinInput = currentPinInput.slice(0, -1);
  updatePinDisplay();
}

function clearPinKeypad() {
  currentPinInput = "";
  updatePinDisplay();
}

function updatePinDisplay() {
  const el = document.getElementById("pinDisplay");
  if (!el) return;
  el.textContent = currentPinInput.padEnd(4, "_").split("").join(" ");
}

async function submitPodPin() {
  if (currentPinInput.length !== 4) {
    showToast("Please enter the complete 4-digit customer PIN", "error");
    return;
  }

  try {
    const res = await fetch(`${window.location.origin}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        order_id: activePodOrderId,
        new_status: "DELIVERED",
        verification_pin: currentPinInput,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "PIN verification failed");
    }

    closePodModal();
    showToast("Proof of Delivery Verified! Order successfully completed.", "success");
    playDeliveryChime();
    loadRiderTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function simulateQrScanPod() {
  if (!activePodOrderId || !activePodToken) return;

  try {
    const res = await fetch(`${window.location.origin}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        order_id: activePodOrderId,
        new_status: "DELIVERED",
        qr_token: activePodToken,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "QR token verification failed");
    }

    closePodModal();
    showToast("QR Token Matched! Proof of Delivery verified successfully.", "success");
    playDeliveryChime();
    loadRiderTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==================================================
// Audio Delivery Confirmation Chime
// ==================================================

function playDeliveryChime() {
  try {
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate([100, 50, 100, 50, 150]);
    }
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === "suspended") ctx.resume().catch(() => {});

    [
      { freq: 523.25, time: 0.0, dur: 0.12 },
      { freq: 659.25, time: 0.12, dur: 0.12 },
      { freq: 783.99, time: 0.24, dur: 0.25 },
    ].forEach(({ freq, time, dur }) => {
      try {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, ctx.currentTime + time);
        gain.gain.setValueAtTime(0.15, ctx.currentTime + time);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + time + dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + time);
        osc.stop(ctx.currentTime + time + dur);
      } catch (e) {
        // Non-fatal
      }
    });
  } catch (e) {
    // Non-fatal: audio not supported
  }
}

// ==================================================
// Inline SVG Icon Helpers (Heroicons style)
// ==================================================

function svgRider(size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="17.5" r="3"/><circle cx="18.5" cy="17.5" r="3"/><path d="M15 6h2l2 4.5-5 2-2-4H9l-1.5 5.5M9 6l1.5 4.5"/><circle cx="10" cy="4" r="1"/></svg>`;
}

function svgPackage(size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/></svg>`;
}

function svgPin(size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`;
}

function svgLock(size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`;
}

function svgCheckCircle(size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
}

// ==================================================
// Global Exports for HTML Inline Handlers
// Modules do not auto-expose to window; these explicit bindings
// allow onclick attributes in index.html to call these functions.
// ==================================================

window.handleLoginSubmit = handleLoginSubmit;
window.quickLogin = quickLogin;
window.logoutUser = logout;
window.logout = logout;
window.toggleTheme = toggleTheme;
window.openCreateOrderModal = openCreateOrderModal;
window.closeCreateOrderModal = closeCreateOrderModal;
window.handleCreateOrderSubmit = handleCreateOrderSubmit;
window.loadDispatcherDashboard = () => loadDispatcherDashboard(false);
window.switchDispatchQueue = switchDispatchQueue;
window.assignOrderToRider = assignOrderToRider;
window.loadRiderTasks = () => loadRiderTasks(false);
window.closePodModal = closePodModal;
window.appendPinDigit = appendPinDigit;
window.clearPinKeypad = clearPinKeypad;
window.backspacePinDigit = backspacePinDigit;
window.submitPodPin = submitPodPin;
window.simulateQrScanPod = simulateQrScanPod;
window.switchPersonaView = switchPersonaView;
window.triggerRiderMilestone = triggerRiderMilestone;
window.openPodModal = openPodModal;
