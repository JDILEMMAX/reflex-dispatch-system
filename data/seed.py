"""Database initialization and seeding module for Reflex Delivery System."""

import os
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "reflex.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")

DEFAULT_PASSWORD = "Reflex2026!"


def get_password_hash(password: str) -> str:
    """Generate secure bcrypt password hash."""
    return pwd_context.hash(password)


def init_db(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH) -> sqlite3.Connection:
    """Initialize database tables and indexes from schema.sql."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    return conn


def seed_data(conn: sqlite3.Connection) -> None:
    """Seed demo accounts, riders, sample delivery orders and audit logs."""
    cursor = conn.cursor()

    # Clear existing data in reverse dependency order
    cursor.execute("DELETE FROM notification_events;")
    cursor.execute("DELETE FROM status_logs;")
    cursor.execute("DELETE FROM delivery_orders;")
    cursor.execute("DELETE FROM riders;")
    cursor.execute("DELETE FROM users;")

    hashed_pw = get_password_hash(DEFAULT_PASSWORD)

    # 1. Seed User Accounts
    users = [
        ("luthuli_electronics", hashed_pw, "ROLE_RETAILER", "Maina K. (Luthuli Electronics)", "+254712345678"),
        ("cbd_pharmacy", hashed_pw, "ROLE_RETAILER", "Dr. Achieng O. (CBD Chemist)", "+254723456789"),
        ("nairobi_dispatch", hashed_pw, "ROLE_DISPATCHER", "Kamau N. (Nairobi Central Hub)", "+254734567890"),
        ("rider_mwangi", hashed_pw, "ROLE_RIDER", "John Mwangi", "+254745678901"),
        ("rider_otieno", hashed_pw, "ROLE_RIDER", "Peter Otieno", "+254756789012"),
    ]

    cursor.executemany(
        """
        INSERT INTO users (username, password_hash, role, full_name, phone)
        VALUES (?, ?, ?, ?, ?);
        """,
        users,
    )

    # Map username to user_id
    cursor.execute("SELECT id, username FROM users;")
    user_map = {row["username"]: row["id"] for row in cursor.fetchall()}

    # 2. Seed Rider Telemetry
    riders = [
        (user_map["rider_mwangi"], "Motorcycle (Boxer 150)", "KMDF 420X", "+254745678901", 1),
        (user_map["rider_otieno"], "Motorcycle (TVS Star)", "KMEB 819Y", "+254756789012", 1),
    ]

    cursor.executemany(
        """
        INSERT INTO riders (user_id, vehicle_type, vehicle_plate, phone_number, is_active)
        VALUES (?, ?, ?, ?, ?);
        """,
        riders,
    )

    # Map user_id to rider_id
    cursor.execute("SELECT id, user_id FROM riders;")
    rider_map = {row["user_id"]: row["id"] for row in cursor.fetchall()}
    rider_mwangi_id = rider_map[user_map["rider_mwangi"]]
    rider_otieno_id = rider_map[user_map["rider_otieno"]]

    #issue #3- Add secondary pharmacy or Hardaware store
    secondary_retailers =[
        ("westlands_pharmacy",hashed_pw,"ROLE_RETAILER","Dr. Fatma S. (Westland Pharmacy)","+254700111222"),
        ("industrial_hardware",hashed_pw,"ROLE_RETAILER","Otieno J. (Industrial Area Hardware)","+254700333444"),
    ]
    cursor.executemany(
        """
        INSERT INTO users (username,password_hash,role,full_name,phone)
        VALUES (?, ?, ?, ?, ?);
        """,
        secondary_retailers,
    )
    cursor.execute("SELECT id,username From users;")
    user_map ={row["username"]: row["id"]for row in cursor.fetchall()}
    
    # 3. Seed Sample Delivery Orders
    orders = [
        (
            user_map["luthuli_electronics"],
            None,
            "REF-8492-X1",
            "Wanjiku Kamau",
            "+254701234567",
            "Bazaar Plaza, 4th Floor, Upper Hill, Nairobi",
            "HP Laptop Charger & Wireless Mouse",
            3500.0,
            300.0,
            "ORDER_LOGGED",
            "4829",
            None,
            None,
            None,
        ),
        (
            user_map["cbd_pharmacy"],
            rider_mwangi_id,
            "REF-5120-K9",
            "Brian Omondi",
            "+254711987654",
            "Delta Corner, Tower A, Westlands, Nairobi",
            "Prescription Medicine & First Aid Pack",
            5200.0,
            450.0,
            "ASSIGNED",
            "7314",
            "2026-08-28 08:30:00",
            None,
            None,
        ),
        (
            user_map["luthuli_electronics"],
            rider_otieno_id,
            "REF-3094-M3",
            "Esther Muthoni",
            "+254722556677",
            "KICC Building, 12th Floor, Harambee Ave, Nairobi",
            "Sony Noise-Cancelling Headphones",
            12000.0,
            500.0,
            "PICKED_UP",
            "9182",
            "2026-08-28 07:15:00",
            "2026-08-28 07:45:00",
            None,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO delivery_orders (
            retailer_id, rider_id, tracking_token, customer_name, customer_phone,
            delivery_address, item_description, package_value, delivery_fee,
            status, verification_pin, assigned_at, picked_up_at, delivered_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        orders,
    )

    # 4. Seed Status Audit Logs for Initial Orders
    cursor.execute("SELECT id, tracking_token, status, retailer_id, rider_id FROM delivery_orders;")
    order_records = {row["tracking_token"]: row for row in cursor.fetchall()}

    # Order 1 status log
    o1 = order_records["REF-8492-X1"]
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, NULL, 'ORDER_LOGGED', 'Order logged by retailer staff with generated PIN');
        """,
        (o1["id"], o1["retailer_id"]),
    )

    # Order 2 status logs (ORDER_LOGGED -> ASSIGNED)
    o2 = order_records["REF-5120-K9"]
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, NULL, 'ORDER_LOGGED', 'Order logged by pharmacy retailer');
        """,
        (o2["id"], o2["retailer_id"]),
    )
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, 'ORDER_LOGGED', 'ASSIGNED', 'Assigned to rider John Mwangi (KMDF 420X)');
        """,
        (o2["id"], user_map["nairobi_dispatch"]),
    )

    # Order 3 status logs (ORDER_LOGGED -> ASSIGNED -> PICKED_UP)
    o3 = order_records["REF-3094-M3"]
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, NULL, 'ORDER_LOGGED', 'Order logged by electronics retailer');
        """,
        (o3["id"], o3["retailer_id"]),
    )
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, 'ORDER_LOGGED', 'ASSIGNED', 'Assigned to rider Peter Otieno (KMEB 819Y)');
        """,
        (o3["id"], user_map["nairobi_dispatch"]),
    )
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes)
        VALUES (?, ?, 'ASSIGNED', 'PICKED_UP', 'Package picked up from shop by rider Peter Otieno');
        """,
        (o3["id"], user_map["rider_otieno"]),
    )

    conn.commit()
    print("[REFLEX] Database seeded successfully with demo accounts and initial orders.")


if __name__ == "__main__":
    connection = init_db()
    seed_data(connection)
    connection.close()
