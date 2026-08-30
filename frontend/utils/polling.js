/**
 * polling.js - Live polling engine for the Reflex Delivery System.
 * Callback-based design with no direct DOM or API dependencies.
 */

let _timer = null;

/**
 * Start a repeating poll interval, stopping any existing one first.
 * @param {Function} callback - Async function to call on each tick.
 * @param {number} intervalMs - Polling interval in milliseconds (default 3000).
 */
export function startPolling(callback, intervalMs = 3000) {
  stopPolling();
  _timer = setInterval(callback, intervalMs);
}

/** Stop the active poll interval, if any. */
export function stopPolling() {
  if (_timer !== null) {
    clearInterval(_timer);
    _timer = null;
  }
}

/** Returns true if a poll is currently running. */
export function isPolling() {
  return _timer !== null;
}
