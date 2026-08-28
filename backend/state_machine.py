"""Deterministic delivery state machine and dual-factor Proof of Delivery (POD) engine."""

from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

VALID_TRANSITIONS = {
    "ORDER_LOGGED": ["ASSIGNED", "CANCELLED"],
    "ASSIGNED": ["PICKED_UP", "CANCELLED"],
    "PICKED_UP": ["ARRIVED"],
    "ARRIVED": ["DELIVERED"],
    "DELIVERED": [],
    "CANCELLED": [],
}


def validate_pod_token(order: sqlite3.Row, verification_pin: Optional[str], qr_token: Optional[str]) -> bool:
    """Validate dual-factor Proof of Delivery token against database record."""
    if verification_pin and str(verification_pin).strip() == str(order["verification_pin"]).strip():
        return True
    if qr_token and str(qr_token).strip() == str(order["tracking_token"]).strip():
        return True
    return False


def transition_order_state(
    conn: sqlite3.Connection,
    order_id: int,
    new_status: str,
    current_user: Dict[str, Any],
    rider_id: Optional[int] = None,
    verification_pin: Optional[str] = None,
    qr_token: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute deterministic state transition with strict RBAC, POD and atomic audit logging."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delivery_orders WHERE id = ?;", (order_id,))
    order = cursor.fetchone()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery order #{order_id} was not found",
        )

    current_status = order["status"]
    allowed_next = VALID_TRANSITIONS.get(current_status, [])

    if new_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Illegal state transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed_next}",
        )

    user_role = current_user["role"]
    user_id = current_user["id"]
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Specific Transition Rules and Security Gate Checks
    if new_status == "ASSIGNED":
        if user_role not in ["ROLE_DISPATCHER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only dispatchers are authorized to assign orders to riders",
            )
        if not rider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rider selection is required when assigning an order",
            )
        cursor.execute("SELECT id, is_active FROM riders WHERE id = ?;", (rider_id,))
        rider_row = cursor.fetchone()
        if not rider_row or rider_row["is_active"] != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target rider is not registered or currently inactive in the fleet",
            )

        cursor.execute(
            """
            UPDATE delivery_orders
            SET status = 'ASSIGNED', rider_id = ?, assigned_at = ?
            WHERE id = ?;
            """,
            (rider_id, now_iso, order_id),
        )
        default_note = f"Assigned to rider #{rider_id} by dispatcher {current_user['username']}"

    elif new_status == "PICKED_UP":
        if user_role not in ["ROLE_RIDER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned rider can confirm package pickup",
            )
        rider_profile_id = current_user.get("rider_id")
        if order["rider_id"] != rider_profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned rider for this delivery order",
            )

        cursor.execute(
            """
            UPDATE delivery_orders
            SET status = 'PICKED_UP', picked_up_at = ?
            WHERE id = ?;
            """,
            (now_iso, order_id),
        )
        default_note = "Physical package custody confirmed by rider at retail store"

    elif new_status == "ARRIVED":
        if user_role not in ["ROLE_RIDER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned rider can update arrival status",
            )
        rider_profile_id = current_user.get("rider_id")
        if order["rider_id"] != rider_profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned rider for this delivery order",
            )

        cursor.execute(
            """
            UPDATE delivery_orders
            SET status = 'ARRIVED'
            WHERE id = ?;
            """,
            (order_id,),
        )
        default_note = "Rider arrived at destination address"

    elif new_status == "DELIVERED":
        if user_role not in ["ROLE_RIDER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned rider can finalize delivery verification",
            )
        rider_profile_id = current_user.get("rider_id")
        if order["rider_id"] != rider_profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the assigned rider for this delivery order",
            )

        # Dual-Factor POD Verification (Customer PIN or Scanned QR Token)
        if not validate_pod_token(order, verification_pin, qr_token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Proof of Delivery PIN or QR token. Handoff verification rejected.",
            )

        cursor.execute(
            """
            UPDATE delivery_orders
            SET status = 'DELIVERED', delivered_at = ?
            WHERE id = ?;
            """,
            (now_iso, order_id),
        )
        default_note = "Doorstep Proof of Delivery verified via customer PIN/QR handshake"

    elif new_status == "CANCELLED":
        if user_role not in ["ROLE_RETAILER", "ROLE_DISPATCHER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only retailers or dispatchers are authorized to cancel orders",
            )
        if user_role == "ROLE_RETAILER" and order["retailer_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Retailers can only cancel orders originating from their store",
            )

        cursor.execute(
            """
            UPDATE delivery_orders
            SET status = 'CANCELLED'
            WHERE id = ?;
            """,
            (order_id,),
        )
        default_note = notes or f"Order cancelled by {current_user['username']}"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unhandled status transition: {new_status}",
        )

    # Append to immutable status audit log
    final_notes = notes or default_note
    cursor.execute(
        """
        INSERT INTO status_logs (order_id, changed_by_user_id, previous_status, new_status, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (order_id, user_id, current_status, new_status, final_notes, now_iso),
    )

    # Enqueue async notification event
    event_payload = json.dumps({
        "order_id": order_id,
        "tracking_token": order["tracking_token"],
        "customer_phone": order["customer_phone"],
        "previous_status": current_status,
        "new_status": new_status,
        "timestamp": now_iso,
    })
    cursor.execute(
        """
        INSERT INTO notification_events (order_id, event_type, payload_json, delivery_status)
        VALUES (?, 'STATUS_CHANGED', ?, 'PENDING');
        """,
        (order_id, event_payload),
    )

    conn.commit()

    # Return refreshed order record
    cursor.execute("SELECT * FROM delivery_orders WHERE id = ?;", (order_id,))
    updated_row = cursor.fetchone()
    return dict(updated_row)
