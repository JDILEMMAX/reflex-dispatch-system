/**
 * Reflex Client Application Controller & State Engine
 * Handles JWT sessions, role-based views, dynamic polling and Proof of Delivery verification.
 */

const API_BASE = window.location.origin;

// Application State
let currentAuth = null;
let currentQueueFilter = "UNASSIGNED";
let allDispatchOrders = [];
let allRiders = [];
let pollingTimer = null;

// POD Keypad State
let activePodOrderId = null;
let activePodToken = null;
let currentPinInput = "";

// ==================================================
// Initialization & Session Management
// ==================================================

document.addEventListener("DOMContentLoaded", () => {
  restoreSession();
});

function restoreSession() {
  const token = localStorage.getItem("reflex_token");
  const userData = localStorage.getItem("reflex_user");

  if (token && userData) {
    try {
      currentAuth = {
        token: token,
        user: JSON.parse(userData),
      };
      updateHeaderProfile();
      routeUserView(currentAuth.user.role);
      startLivePolling();
      return;
    } catch (e) {
      console.error("Failed to restore stored session:", e);
    }
  }
  showView("viewLogin");
}

function updateHeaderProfile() {
  const profileEl = document.getElementById("userHeaderProfile");
  const badgeText = document.getElementById("roleBadgeText");
  const nameEl = document.getElementById("userDisplayName");

  if (currentAuth && currentAuth.user) {
    profileEl.style.display = "flex";
    badgeText.textContent = currentAuth.user.role.replace("ROLE_", "");
    nameEl.textContent = currentAuth.user.full_name || currentAuth.user.username;
  } else {
    profileEl.style.display = "none";
  }
}

function showView(viewId) {
  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.remove("active");
  });
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add("active");
  }
}

function routeUserView(role) {
  if (role === "ROLE_RETAILER") {
    showView("viewRetailer");
    loadRetailerDashboard();
  } else if (role === "ROLE_DISPATCHER") {
    showView("viewDispatcher");
    loadDispatcherDashboard();
  } else if (role === "ROLE_RIDER") {
    showView("viewRider");
    loadRiderTasks();
  } else {
    showView("viewLogin");
  }
}

// ==================================================
// Authentication Handlers
// ==================================================

async function handleLoginSubmit(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value.trim();

  await performLogin(username, password);
}

async function quickLogin(username, password) {
  document.getElementById("loginUsername").value = username;
  document.getElementById("loginPassword").value = password;
  await performLogin(username, password);
}

async function performLogin(username, password) {
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Invalid credentials");
    }

    const data = await res.json();
    currentAuth = {
      token: data.access_token,
      user: {
        id: data.user_id,
        username: data.username,
        role: data.role,
        full_name: data.full_name,
        rider_id: data.rider_id,
      },
    };

    localStorage.setItem("reflex_token", currentAuth.token);
    localStorage.setItem("reflex_user", JSON.stringify(currentAuth.user));

    updateHeaderProfile();
    routeUserView(currentAuth.user.role);
    startLivePolling();
    showToast(`Authenticated as ${currentAuth.user.full_name}`, "success");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function logoutUser() {
  stopLivePolling();
  localStorage.removeItem("reflex_token");
  localStorage.removeItem("reflex_user");
  currentAuth = null;
  updateHeaderProfile();
  showView("viewLogin");
  showToast("Logged out successfully", "success");
}

function getAuthHeaders() {
  if (!currentAuth || !currentAuth.token) return {};
  return {
    "Authorization": `Bearer ${currentAuth.token}`,
    "Content-Type": "application/json",
  };
}

// ==================================================
// Polling Loop (3-Second Live Refresh)
// ==================================================

function startLivePolling() {
  stopLivePolling();
  pollingTimer = setInterval(() => {
    if (!currentAuth) return;
    if (currentAuth.user.role === "ROLE_RETAILER") {
      loadRetailerDashboard(true);
    } else if (currentAuth.user.role === "ROLE_DISPATCHER") {
      loadDispatcherDashboard(true);
    } else if (currentAuth.user.role === "ROLE_RIDER") {
      loadRiderTasks(true);
    }
  }, 3000);
}

function stopLivePolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

// ==================================================
// Retailer Dashboard Methods
// ==================================================

async function loadRetailerDashboard(isSilent = false) {
  try {
    const res = await fetch(`${API_BASE}/api/orders/retailer`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load retailer orders");

    const orders = await res.json();
    renderRetailerOrdersTable(orders);

    // Compute Metrics
    const total = orders.length;
    const active = orders.filter((o) => ["ORDER_LOGGED", "ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status)).length;
    const delivered = orders.filter((o) => o.status === "DELIVERED").length;

    document.getElementById("statRetailerTotal").textContent = total;
    document.getElementById("statRetailerActive").textContent = active;
    document.getElementById("statRetailerDelivered").textContent = delivered;
  } catch (err) {
    if (!isSilent) showToast(err.message, "error");
  }
}

function renderRetailerOrdersTable(orders) {
  const tbody = document.getElementById("retailerOrdersBody");
  if (!tbody) return;

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2rem;">No delivery orders logged yet. Click '+ Log New Delivery Request' to start.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map((o) => `
    <tr>
      <td>
        <a href="/track/${o.tracking_token}" target="_blank" class="token-pill" title="Open Customer Live Tracker">
          ${o.tracking_token} ↗
        </a>
      </td>
      <td>
        <strong>${escapeHtml(o.customer_name)}</strong><br>
        <small style="color: var(--text-muted);">${escapeHtml(o.customer_phone)}</small>
      </td>
      <td style="max-width: 200px;">
        <span style="font-size: 0.85rem;">${escapeHtml(o.delivery_address)}</span>
      </td>
      <td>
        <strong>${escapeHtml(o.item_description)}</strong><br>
        <small style="color: var(--accent-cyan);">KES ${Number(o.package_value).toLocaleString()}</small>
      </td>
      <td>
        <span style="color: var(--text-secondary);">KES ${Number(o.delivery_fee).toLocaleString()}</span>
      </td>
      <td>
        <span class="status-badge status-${o.status}">${o.status.replace("_", " ")}</span>
      </td>
      <td>
        <span class="pin-tag">PIN: ${o.verification_pin}</span>
      </td>
      <td>
        ${o.rider_name ? `🛵 ${escapeHtml(o.rider_name)}<br><small style="color: var(--text-muted);">${escapeHtml(o.vehicle_plate || "")}</small>` : `<span style="color: var(--text-muted); font-style: italic;">Unassigned</span>`}
      </td>
      <td>
        <a href="/track/${o.tracking_token}" target="_blank" class="btn-secondary" style="padding: 0.35rem 0.6rem; font-size: 0.75rem; text-decoration: none;">
          Track Link
        </a>
      </td>
    </tr>
  `).join("");
}

function openCreateOrderModal() {
  document.getElementById("createOrderForm").reset();
  document.getElementById("modalCreateOrder").classList.add("active");
}

function closeCreateOrderModal() {
  document.getElementById("modalCreateOrder").classList.remove("active");
}

async function handleCreateOrderSubmit(event) {
  event.preventDefault();
  const payload = {
    customer_name: document.getElementById("orderCustomerName").value.trim(),
    customer_phone: document.getElementById("orderCustomerPhone").value.trim(),
    delivery_address: document.getElementById("orderAddress").value.trim(),
    item_description: document.getElementById("orderItemDesc").value.trim(),
    package_value: parseFloat(document.getElementById("orderValue").value) || 0,
    delivery_fee: parseFloat(document.getElementById("orderFee").value) || 0,
  };

  try {
    const res = await fetch(`${API_BASE}/api/orders`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to log delivery order");
    }

    const createdOrder = await res.json();
    closeCreateOrderModal();
    showToast(`Order logged successfully! Token: ${createdOrder.tracking_token} (PIN: ${createdOrder.verification_pin})`, "success");
    loadRetailerDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==================================================
// Dispatcher Command Board Methods
// ==================================================

async function loadDispatcherDashboard(isSilent = false) {
  try {
    const [ordersRes, ridersRes] = await Promise.all([
      fetch(`${API_BASE}/api/dispatch/orders`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE}/api/dispatch/riders`, { headers: getAuthHeaders() }),
    ]);

    if (!ordersRes.ok || !ridersRes.ok) throw new Error("Failed to load dispatch datasets");

    allDispatchOrders = await ordersRes.json();
    allRiders = await ridersRes.json();

    updateDispatchQueueCounts();
    renderDispatcherOrdersTable();
    renderRiderRoster();
  } catch (err) {
    if (!isSilent) showToast(err.message, "error");
  }
}

function updateDispatchQueueCounts() {
  const unassigned = allDispatchOrders.filter((o) => o.status === "ORDER_LOGGED").length;
  const inTransit = allDispatchOrders.filter((o) => ["ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status)).length;
  const delivered = allDispatchOrders.filter((o) => o.status === "DELIVERED").length;

  document.getElementById("countUnassigned").textContent = unassigned;
  document.getElementById("countInTransit").textContent = inTransit;
  document.getElementById("countDelivered").textContent = delivered;
}

function switchDispatchQueue(queueName) {
  currentQueueFilter = queueName;
  document.querySelectorAll(".queue-tab-btn").forEach((btn) => btn.classList.remove("active"));
  if (queueName === "UNASSIGNED") document.getElementById("tabUnassigned").classList.add("active");
  if (queueName === "IN_TRANSIT") document.getElementById("tabInTransit").classList.add("active");
  if (queueName === "DELIVERED") document.getElementById("tabDelivered").classList.add("active");

  renderDispatcherOrdersTable();
}

function renderDispatcherOrdersTable() {
  const tbody = document.getElementById("dispatcherOrdersBody");
  if (!tbody) return;

  let filtered = [];
  if (currentQueueFilter === "UNASSIGNED") {
    filtered = allDispatchOrders.filter((o) => o.status === "ORDER_LOGGED");
  } else if (currentQueueFilter === "IN_TRANSIT") {
    filtered = allDispatchOrders.filter((o) => ["ASSIGNED", "PICKED_UP", "ARRIVED"].includes(o.status));
  } else if (currentQueueFilter === "DELIVERED") {
    filtered = allDispatchOrders.filter((o) => o.status === "DELIVERED");
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No orders currently in this queue.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((o) => `
    <tr>
      <td>
        <a href="/track/${o.tracking_token}" target="_blank" class="token-pill">
          ${o.tracking_token} ↗
        </a>
      </td>
      <td>
        <strong>${escapeHtml(o.retailer_name || "Merchant")}</strong><br>
        <small style="color: var(--text-muted);">${escapeHtml(o.retailer_phone || "")}</small>
      </td>
      <td style="max-width: 220px;">
        <strong>${escapeHtml(o.customer_name)}</strong> (${escapeHtml(o.customer_phone)})<br>
        <small style="color: var(--text-secondary);">${escapeHtml(o.delivery_address)}</small>
      </td>
      <td>
        <span>${escapeHtml(o.item_description)}</span><br>
        <small style="color: var(--accent-cyan);">KES ${Number(o.package_value).toLocaleString()}</small>
      </td>
      <td>
        <span class="status-badge status-${o.status}">${o.status.replace("_", " ")}</span>
      </td>
      <td>
        ${o.rider_name ? `🛵 ${escapeHtml(o.rider_name)}<br><small style="color: var(--text-muted);">${escapeHtml(o.vehicle_plate || "")}</small>` : `<span style="color: var(--accent-amber); font-weight: 600;">Needs Assignment</span>`}
      </td>
      <td>
        ${o.status === "ORDER_LOGGED" ? `
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <select class="form-select" id="assign_select_${o.id}" style="padding: 0.35rem 0.5rem; font-size: 0.8rem; width: 140px;">
              <option value="">Select Rider...</option>
              ${allRiders.map((r) => `<option value="${r.id}">${escapeHtml(r.full_name)} (${escapeHtml(r.vehicle_plate)})</option>`).join("")}
            </select>
            <button class="btn-primary" onclick="assignOrderToRider(${o.id})" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; width: auto;">
              Assign
            </button>
          </div>
        ` : `
          <a href="/track/${o.tracking_token}" target="_blank" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; text-decoration: none;">
            Live Stepper
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
    const res = await fetch(`${API_BASE}/api/dispatch/assign`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ order_id: orderId, rider_id: riderId }),
    });

    if (!res.ok) {
      const err = await res.json();
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

  container.innerHTML = allRiders.map((r) => `
    <div class="rider-card">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div class="rider-avatar">🛵</div>
        <div>
          <strong style="font-size: 0.9rem;">${escapeHtml(r.full_name)}</strong><br>
          <small style="color: var(--text-muted);">${escapeHtml(r.vehicle_plate)} • ${escapeHtml(r.phone_number)}</small>
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
// Rider Mobile Terminal Methods
// ==================================================

async function loadRiderTasks(isSilent = false) {
  try {
    const res = await fetch(`${API_BASE}/api/rider/tasks`, {
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
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">🛵</div>
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
          <div>
            <span class="token-pill">${t.tracking_token}</span>
          </div>
          <span class="status-badge status-${t.status}">${t.status.replace("_", " ")}</span>
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
            ${escapeHtml(t.item_description)} • <strong style="color: var(--accent-green);">Fee: KES ${Number(t.delivery_fee).toLocaleString()}</strong>
          </div>
        </div>

        <div class="task-actions">
          ${t.status === "ASSIGNED" ? `
            <button class="btn-milestone btn-milestone-pickup" onclick="triggerRiderMilestone(${t.id}, 'PICKED_UP')">
              📦 Confirm Shop Package Pickup
            </button>
          ` : ""}

          ${t.status === "PICKED_UP" ? `
            <button class="btn-milestone btn-milestone-arrived" onclick="triggerRiderMilestone(${t.id}, 'ARRIVED')">
              📍 Confirm Arrival at Customer Doorstep
            </button>
          ` : ""}

          ${t.status === "ARRIVED" ? `
            <button class="btn-milestone btn-milestone-pod" onclick="openPodModal(${t.id}, '${t.tracking_token}')">
              🔐 Enter Customer PIN / Scan POD
            </button>
          ` : ""}

          ${t.status === "DELIVERED" ? `
            <div style="text-align: center; color: var(--accent-green); font-weight: 700; font-size: 0.9rem; padding: 0.5rem; background: rgba(0, 230, 118, 0.1); border-radius: var(--radius-sm); border: 1px solid var(--accent-green);">
              ✓ Delivery Verified & Chain of Custody Closed
            </div>
          ` : ""}
        </div>
      </div>
    `;
  }).join("");
}

async function triggerRiderMilestone(orderId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ order_id: orderId, new_status: newStatus }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Milestone update failed");
    }

    showToast(`Status updated to ${newStatus.replace("_", " ")}`, "success");
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
  document.getElementById("podOrderToken").textContent = token;
  updatePinDisplay();
  document.getElementById("modalPodKeypad").classList.add("active");
}

function closePodModal() {
  document.getElementById("modalPodKeypad").classList.remove("active");
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
  const digits = currentPinInput.padEnd(4, "_").split("");
  el.textContent = digits.join(" ");
}

async function submitPodPin() {
  if (currentPinInput.length !== 4) {
    showToast("Please enter the complete 4-digit customer PIN", "error");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        order_id: activePodOrderId,
        new_status: "DELIVERED",
        verification_pin: currentPinInput,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Verification failed");
    }

    closePodModal();
    showToast("Proof of Delivery Verified! Order successfully completed.", "success");
    loadRiderTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function simulateQrScanPod() {
  if (!activePodOrderId || !activePodToken) return;

  try {
    const res = await fetch(`${API_BASE}/api/rider/milestone`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        order_id: activePodOrderId,
        new_status: "DELIVERED",
        qr_token: activePodToken,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "QR Token verification failed");
    }

    closePodModal();
    showToast("QR Token Matched! Proof of Delivery verified successfully.", "success");
    loadRiderTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ==================================================
// Utilities & Toast Notifications
// ==================================================

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast-alert toast-${type}`;
  toast.innerHTML = `
    <span>${type === "success" ? "✓" : "⚠"}</span>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
