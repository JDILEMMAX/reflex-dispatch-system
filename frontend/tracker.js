/**
 * tracker.js - Standalone ES6 module for the public Reflex order tracker.
 * Handles token resolution, live polling, stepper rendering and audit log display.
 *
 * Imports shared helpers from the utils library to avoid duplication.
 */

import { escapeHtml, formatDate } from "./utils/ui.js";

const MILESTONES = [
  "ORDER_LOGGED",
  "ASSIGNED",
  "PICKED_UP",
  "ARRIVED",
  "DELIVERED",
];

let currentTrackingToken = null;
let trackerPollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  const savedTheme = localStorage.getItem("reflex_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);

  // 1. Resolve token from path: /track/{token}
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  if (pathParts.length >= 2 && pathParts[0] === "track") {
    currentTrackingToken = pathParts[1];
  } else {
    // 2. Fallback: resolve from query param ?token=... or ?tracking_token=...
    const urlParams = new URLSearchParams(window.location.search);
    currentTrackingToken = urlParams.get("token") || urlParams.get("tracking_token");
  }

  if (currentTrackingToken && currentTrackingToken !== "tracker.html") {
    fetchTrackingData(currentTrackingToken);
    startTrackerPolling();
  } else {
    // No token in URL - show manual search panel
    const searchPanel = document.getElementById("tokenSearchPanel");
    if (searchPanel) searchPanel.style.display = "block";
  }
});

/**
 * Initiate a manual token lookup from the search input.
 * Exposed to window so the HTML button onclick can call it.
 */
function searchManualToken() {
  const input = document.getElementById("manualTokenInput");
  if (!input || !input.value.trim()) return;
  currentTrackingToken = input.value.trim();
  fetchTrackingData(currentTrackingToken);
  startTrackerPolling();
}

/**
 * Start the 3-second live polling loop, replacing any existing interval.
 */
function startTrackerPolling() {
  if (trackerPollInterval) clearInterval(trackerPollInterval);
  trackerPollInterval = setInterval(() => {
    if (currentTrackingToken) {
      fetchTrackingData(currentTrackingToken, true);
    }
  }, 3000);
}

/**
 * Fetch order data from the backend and render the tracking view.
 * @param {string} token - Tracking token to resolve.
 * @param {boolean} isSilent - If true, suppresses the status message updates.
 */
async function fetchTrackingData(token, isSilent = false) {
  const statusEl = document.getElementById("trackerStatusMsg");
  const cardEl = document.getElementById("trackingDetailsCard");

  if (!isSilent && statusEl) {
    statusEl.style.display = "block";
    statusEl.textContent = `Connecting to Reflex verification network for ${token}...`;
  }

  try {
    const res = await fetch(`${window.location.origin}/api/track/${token}`);
    if (!res.ok) {
      throw new Error(`Tracking record for '${token}' was not found in the ledger.`);
    }

    const data = await res.json();
    renderTrackingView(data);

    if (statusEl) statusEl.style.display = "none";
    if (cardEl) cardEl.style.display = "block";
  } catch (err) {
    if (!isSilent) {
      if (statusEl) {
        statusEl.style.display = "block";
        statusEl.innerHTML = `<span style="color: var(--accent-red);">${svgWarning()} ${err.message}</span>`;
      }
      if (cardEl) cardEl.style.display = "none";
    }
  }
}

/**
 * Populate the tracking card with all order fields, stepper and audit log.
 * @param {Object} data - Order data returned from /api/track/{token}.
 */
function renderTrackingView(data) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  set("trackTokenDisplay", data.tracking_token);
  set("trackCreatedTime", `Logged on ${formatDate(data.created_at) || data.created_at}`);
  set("trackCustomerName", data.customer_name);
  set("trackAddress", data.delivery_address);
  set("trackRetailerName", data.retailer_name || "Merchant Shop");
  set("trackItemDesc", data.item_description);
  set(
    "trackPackageValue",
    `KES ${Number(data.package_value).toLocaleString()} (Delivery Fee: KES ${Number(data.delivery_fee).toLocaleString()})`
  );
  set("trackPinDisplay", data.verification_pin);

  const badge = document.getElementById("trackStatusBadge");
  if (badge) {
    badge.textContent = data.status.replace(/_/g, " ");
    badge.className = `status-badge status-${data.status}`;
  }

  const courierEl = document.getElementById("trackCourierInfo");
  if (courierEl) {
    if (data.rider_name) {
      courierEl.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:0.35rem;">
          ${svgRider(14)} ${escapeHtml(data.rider_name)}
        </span><br>
        <small style="color: var(--text-secondary);">
          ${escapeHtml(data.vehicle_plate || "")}
          ${data.rider_phone ? `&bull; ${escapeHtml(data.rider_phone)}` : ""}
        </small>`;
    } else {
      courierEl.textContent = "Awaiting central fleet assignment";
    }
  }

  updateStepperNodes(data.status);
  renderAuditLogs(data.status_logs);
}

/**
 * Update the milestone stepper node states and progress bar.
 * @param {string} status - Current order status string.
 */
function updateStepperNodes(status) {
  const stepIndex = MILESTONES.indexOf(status);
  const nodeIds = [
    "stepNodeLogged",
    "stepNodeAssigned",
    "stepNodePickedUp",
    "stepNodeArrived",
    "stepNodeDelivered",
  ];

  nodeIds.forEach((nodeId, idx) => {
    const node = document.getElementById(nodeId);
    if (!node) return;
    node.classList.remove("active", "completed");
    if (idx < stepIndex) {
      node.classList.add("completed");
    } else if (idx === stepIndex) {
      node.classList.add("active");
    }
  });

  const progressEl = document.getElementById("stepperProgressBar");
  if (progressEl && stepIndex >= 0) {
    const pct = (stepIndex / (MILESTONES.length - 1)) * 100;
    progressEl.style.width = `${pct}%`;
  }
}

/**
 * Render the immutable chain of custody audit log timeline.
 * @param {Array} logs - Array of status transition log objects.
 */
function renderAuditLogs(logs) {
  const container = document.getElementById("auditLogsTimeline");
  if (!container) return;

  if (!logs || logs.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.82rem;">No milestone transitions recorded.</div>`;
    return;
  }

  container.innerHTML = logs.map((l) => `
    <div class="audit-card">
      <div>
        <strong class="audit-status-tag">${escapeHtml(l.new_status)}</strong>:
        <span style="color: var(--text-primary); font-weight: 500;">${escapeHtml(l.notes || "State transition verified")}</span>
        <div class="audit-meta">
          Audited by ${escapeHtml(l.changed_by_full_name || l.changed_by_username || "System")} (${escapeHtml(l.changed_by_role || "")})
        </div>
      </div>
      <div class="audit-timestamp">
        ${escapeHtml(l.timestamp)}
      </div>
    </div>
  `).join("");
}

// ---------- Inline SVG helpers ----------

function svgRider(size = 16) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="17.5" r="3"/><circle cx="18.5" cy="17.5" r="3"/><path d="M15 6h2l2 4.5-5 2-2-4H9l-1.5 5.5M9 6l1.5 4.5"/><circle cx="10" cy="4" r="1"/></svg>`;
}

function svgWarning(size = 14) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
}

// Expose to window for HTML onclick handlers
window.searchManualToken = searchManualToken;
