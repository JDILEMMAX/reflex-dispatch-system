-- Reflex Core Database DDL Specification
-- Configured for high-throughput Write-Ahead Logging (WAL) and strict referential integrity

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ROLE_RETAILER', 'ROLE_DISPATCHER', 'ROLE_RIDER')),
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS riders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    vehicle_type TEXT NOT NULL DEFAULT 'Motorcycle',
    vehicle_plate TEXT NOT NULL UNIQUE,
    phone_number TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS delivery_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rider_id INTEGER REFERENCES riders(id) ON DELETE SET NULL,
    tracking_token TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    item_description TEXT NOT NULL,
    package_value REAL NOT NULL DEFAULT 0.0 CHECK (package_value >= 0),
    delivery_fee REAL NOT NULL DEFAULT 0.0 CHECK (delivery_fee >= 0),
    status TEXT NOT NULL DEFAULT 'ORDER_LOGGED' CHECK (status IN ('ORDER_LOGGED', 'ASSIGNED', 'PICKED_UP', 'ARRIVED', 'DELIVERED', 'CANCELLED')),
    verification_pin TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    picked_up_at TIMESTAMP,
    delivered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS status_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES delivery_orders(id) ON DELETE CASCADE,
    changed_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES delivery_orders(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (delivery_status IN ('PENDING', 'SENT', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Targeted B-Tree Covering Indexes for Sub-Millisecond Queries
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_tracking_token 
ON delivery_orders(tracking_token);

CREATE INDEX IF NOT EXISTS idx_orders_status 
ON delivery_orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_retailer 
ON delivery_orders(retailer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_rider_status 
ON delivery_orders(rider_id, status);

CREATE INDEX IF NOT EXISTS idx_status_logs_order_id 
ON status_logs(order_id, timestamp ASC);
