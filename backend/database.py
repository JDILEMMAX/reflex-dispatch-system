"""Database connection manager and query helpers for Reflex Delivery System."""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "reflex.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Connection factory configuring WAL mode, foreign keys and 5000ms busy timeout."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[sqlite3.Row]:
    """Retrieve user record by unique username."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    return cursor.fetchone()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    """Retrieve user record by primary key id."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    return cursor.fetchone()


def get_rider_by_user_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    """Retrieve rider profile by associated user_id."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.*, u.full_name, u.username 
        FROM riders r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.user_id = ?;
        """,
        (user_id,),
    )
    return cursor.fetchone()


def get_rider_by_id(conn: sqlite3.Connection, rider_id: int) -> Optional[sqlite3.Row]:
    """Retrieve rider profile by primary key id."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.*, u.full_name, u.username 
        FROM riders r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.id = ?;
        """,
        (rider_id,),
    )
    return cursor.fetchone()


def get_active_riders(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Fetch all active riders in the fleet roster with current assignment counts."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            r.id,
            r.user_id,
            r.vehicle_type,
            r.vehicle_plate,
            r.phone_number,
            r.is_active,
            u.full_name,
            u.username,
            (SELECT COUNT(*) FROM delivery_orders d WHERE d.rider_id = r.id AND d.status IN ('ASSIGNED', 'PICKED_UP', 'ARRIVED')) AS active_tasks_count
        FROM riders r
        JOIN users u ON r.user_id = u.id
        WHERE r.is_active = 1
        ORDER BY r.id ASC;
        """
    )
    return cursor.fetchall()


def create_order(
    conn: sqlite3.Connection,
    retailer_id: int,
    tracking_token: str,
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    item_description: str,
    package_value: float,
    delivery_fee: float,
    verification_pin: str,
) -> sqlite3.Row:
    """Create a new delivery order and record initial status log atomically."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO delivery_orders (
            retailer_id, tracking_token, customer_name, customer_phone,
            delivery_address, item_description, package_value, delivery_fee,
            status, verification_pin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ORDER_LOGGED', ?)
        RETURNING *;
        """,
        (
            retailer_id,
            tracking_token,
            customer_name,
            customer_phone,
            delivery_address,
            item_description,
            package_value,
            delivery_fee,
            verification_pin,
        ),
    )
    order = cursor.fetchone()

    # Log initial status audit entry
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, NULL, 'ORDER_LOGGED', 'Order logged by retailer with generated PIN');
        """,
        (order["id"], retailer_id),
    )

    # Queue initial creation notification
    event_payload = json.dumps({
        "order_id": order["id"],
        "tracking_token": tracking_token,
        "customer_phone": customer_phone,
        "event": "ORDER_CREATED",
        "status": "ORDER_LOGGED",
    })
    cursor.execute(
        """
        INSERT INTO notification_events (order_id, event_type, payload_json, delivery_status)
        VALUES (?, 'ORDER_CREATED', ?, 'PENDING');
        """,
        (order["id"], event_payload),
    )

    conn.commit()
    return order


def get_order_by_id(conn: sqlite3.Connection, order_id: int) -> Optional[sqlite3.Row]:
    """Fetch order details by order_id."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            d.*,
            ret.full_name AS retailer_name,
            ret.phone AS retailer_phone,
            rd.vehicle_type,
            rd.vehicle_plate,
            rd.phone_number AS rider_phone,
            ru.full_name AS rider_name
        FROM delivery_orders d
        JOIN users ret ON d.retailer_id = ret.id
        LEFT JOIN riders rd ON d.rider_id = rd.id
        LEFT JOIN users ru ON rd.user_id = ru.id
        WHERE d.id = ?;
        """,
        (order_id,),
    )
    return cursor.fetchone()


def get_order_by_tracking_token(conn: sqlite3.Connection, tracking_token: str) -> Optional[sqlite3.Row]:
    """Fetch order details by public tracking token."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            d.*,
            ret.full_name AS retailer_name,
            ret.phone AS retailer_phone,
            rd.vehicle_type,
            rd.vehicle_plate,
            rd.phone_number AS rider_phone,
            ru.full_name AS rider_name
        FROM delivery_orders d
        JOIN users ret ON d.retailer_id = ret.id
        LEFT JOIN riders rd ON d.rider_id = rd.id
        LEFT JOIN users ru ON rd.user_id = ru.id
        WHERE d.tracking_token = ?;
        """,
        (tracking_token,),
    )
    return cursor.fetchone()


def get_orders_for_retailer(conn: sqlite3.Connection, retailer_id: int) -> List[sqlite3.Row]:
    """Retrieve all orders created by a specific retailer."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            d.*,
            rd.vehicle_plate,
            ru.full_name AS rider_name,
            rd.phone_number AS rider_phone
        FROM delivery_orders d
        LEFT JOIN riders rd ON d.rider_id = rd.id
        LEFT JOIN users ru ON rd.user_id = ru.id
        WHERE d.retailer_id = ?
        ORDER BY d.created_at DESC;
        """,
        (retailer_id,),
    )
    return cursor.fetchall()


def get_all_orders_for_dispatch(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Retrieve all orders across queues for the dispatch command board."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            d.*,
            ret.full_name AS retailer_name,
            ret.phone AS retailer_phone,
            rd.vehicle_plate,
            ru.full_name AS rider_name,
            rd.phone_number AS rider_phone
        FROM delivery_orders d
        JOIN users ret ON d.retailer_id = ret.id
        LEFT JOIN riders rd ON d.rider_id = rd.id
        LEFT JOIN users ru ON rd.user_id = ru.id
        ORDER BY d.created_at DESC;
        """
    )
    return cursor.fetchall()


def get_tasks_for_rider(conn: sqlite3.Connection, rider_id: int) -> List[sqlite3.Row]:
    """Retrieve tasks assigned to a specific rider."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            d.*,
            ret.full_name AS retailer_name,
            ret.phone AS retailer_phone
        FROM delivery_orders d
        JOIN users ret ON d.retailer_id = ret.id
        WHERE d.rider_id = ?
        ORDER BY 
            CASE d.status
                WHEN 'ASSIGNED' THEN 1
                WHEN 'PICKED_UP' THEN 2
                WHEN 'ARRIVED' THEN 3
                WHEN 'DELIVERED' THEN 4
                ELSE 5
            END,
            d.created_at DESC;
        """,
        (rider_id,),
    )
    return cursor.fetchall()


def get_status_logs_for_order(conn: sqlite3.Connection, order_id: int) -> List[sqlite3.Row]:
    """Fetch status audit logs for an order ordered chronologically."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            s.*,
            u.username AS changed_by_username,
            u.full_name AS changed_by_full_name,
            u.role AS changed_by_role
        FROM status_logs s
        JOIN users u ON s.changed_by_user_id = u.id
        WHERE s.order_id = ?
        ORDER BY s.timestamp ASC, s.id ASC;
        """,
        (order_id,),
    )
    return cursor.fetchall()
