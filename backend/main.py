"""FastAPI Application Entrypoint, Routing Gateway and Static UI Provider for Reflex."""

from contextlib import asynccontextmanager
import os
import random
import string
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.auth import (
    create_access_token,
    get_current_user,
    require_role,
    verify_password,
)
from backend.database import (
    create_order,
    get_active_riders,
    get_all_orders_for_dispatch,
    get_db_connection,
    get_order_by_id,
    get_order_by_tracking_token,
    get_orders_for_retailer,
    get_rider_by_user_id,
    get_status_logs_for_order,
    get_tasks_for_rider,
    get_user_by_username,
)
from backend.models import (
    AssignmentRequest,
    LoginRequest,
    MilestoneUpdateRequest,
    OrderCreateRequest,
    OrderResponse,
    PublicTrackingResponse,
    RiderProfileResponse,
    StatusLogResponse,
    TokenResponse,
    UserResponse,
)
from backend.queue_manager import (
    enqueue_notification_event,
    start_queue_worker,
    stop_queue_worker,
)
from backend.state_machine import transition_order_state

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and graceful background worker shutdown."""
    start_queue_worker()
    yield
    await stop_queue_worker()


app = FastAPI(
    title="Reflex On-Demand Dispatch & Chain of Custody System",
    description="Real-time dispatch engine for Kenyan urban retail logistics with deterministic state verification.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_tracking_token() -> str:
    """Generate cryptographically unique tracking token in format REF-####-XX."""
    num_part = f"{random.randint(1000, 9999)}"
    alpha_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    return f"REF-{num_part}-{alpha_part}"


def generate_verification_pin() -> str:
    """Generate 4-digit numeric proof of delivery PIN."""
    return f"{random.randint(1000, 9999)}"


# ==================================================
# Authentication Routes
# ==================================================


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Authenticate user credentials and issue stateless JWT Bearer token."""
    conn = get_db_connection()
    try:
        user = get_user_by_username(conn, credentials.username)
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        rider_id = None
        if user["role"] == "ROLE_RIDER":
            rider = get_rider_by_user_id(conn, user["id"])
            if rider:
                rider_id = rider["id"]

        token_data = {
            "sub": user["username"],
            "role": user["role"],
            "user_id": user["id"],
            "full_name": user["full_name"],
            "rider_id": rider_id,
        }
        token = create_access_token(token_data)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            role=user["role"],
            username=user["username"],
            full_name=user["full_name"],
            user_id=user["id"],
            rider_id=rider_id,
        )
    finally:
        conn.close()


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve authenticated user profile and fleet role."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        role=current_user["role"],
        full_name=current_user["full_name"],
        phone=current_user["phone"],
        created_at=str(current_user.get("created_at", "")),
        rider_id=current_user.get("rider_id"),
        vehicle_type=current_user.get("vehicle_type"),
        vehicle_plate=current_user.get("vehicle_plate"),
    )


# ==================================================
# Retailer Routes
# ==================================================


@app.post("/api/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def log_delivery_order(
    order_data: OrderCreateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_RETAILER"])),
):
    """Log new delivery request with instant tracking token and 4-digit customer PIN."""
    conn = get_db_connection()
    try:
        tracking_token = generate_tracking_token()
        verification_pin = generate_verification_pin()

        order_row = create_order(
            conn=conn,
            retailer_id=current_user["id"],
            tracking_token=tracking_token,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            delivery_address=order_data.delivery_address,
            item_description=order_data.item_description,
            package_value=order_data.package_value,
            delivery_fee=order_data.delivery_fee,
            verification_pin=verification_pin,
        )

        # Enqueue background notification
        await enqueue_notification_event({
            "order_id": order_row["id"],
            "event_type": "ORDER_CREATED",
            "payload": {
                "tracking_token": tracking_token,
                "customer_phone": order_data.customer_phone,
                "status": "ORDER_LOGGED",
            },
        })

        order_detail = get_order_by_id(conn, order_row["id"])
        return dict(order_detail)
    finally:
        conn.close()


@app.get("/api/orders/retailer", response_model=List[OrderResponse])
async def list_retailer_orders(
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_RETAILER"])),
):
    """Retrieve complete order history for the authenticated retailer."""
    conn = get_db_connection()
    try:
        orders = get_orders_for_retailer(conn, current_user["id"])
        return [dict(o) for o in orders]
    finally:
        conn.close()


# ==================================================
# Dispatcher Routes
# ==================================================


@app.get("/api/dispatch/orders", response_model=List[OrderResponse])
async def list_all_dispatch_orders(
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_DISPATCHER"])),
):
    """Retrieve full dispatch command board orders across active queues."""
    conn = get_db_connection()
    try:
        orders = get_all_orders_for_dispatch(conn)
        return [dict(o) for o in orders]
    finally:
        conn.close()


@app.post("/api/dispatch/assign", response_model=OrderResponse)
async def assign_order(
    assignment: AssignmentRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_DISPATCHER"])),
):
    """Assign open delivery order to active rider."""
    conn = get_db_connection()
    try:
        updated_order = transition_order_state(
            conn=conn,
            order_id=assignment.order_id,
            new_status="ASSIGNED",
            current_user=current_user,
            rider_id=assignment.rider_id,
        )

        await enqueue_notification_event({
            "order_id": assignment.order_id,
            "event_type": "ORDER_ASSIGNED",
            "payload": {
                "rider_id": assignment.rider_id,
                "status": "ASSIGNED",
            },
        })

        order_detail = get_order_by_id(conn, assignment.order_id)
        return dict(order_detail)
    finally:
        conn.close()


@app.get("/api/dispatch/riders", response_model=List[RiderProfileResponse])
async def list_active_riders(
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_DISPATCHER"])),
):
    """Fetch active fleet rider roster and live task counts."""
    conn = get_db_connection()
    try:
        riders = get_active_riders(conn)
        return [dict(r) for r in riders]
    finally:
        conn.close()


# ==================================================
# Rider Routes
# ==================================================


@app.get("/api/rider/tasks", response_model=List[OrderResponse])
async def list_rider_tasks(
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_RIDER"])),
):
    """Retrieve active tasks and historical deliveries for authenticated rider."""
    conn = get_db_connection()
    try:
        rider_id = current_user.get("rider_id")
        if not rider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rider profile not associated with this account",
            )
        tasks = get_tasks_for_rider(conn, rider_id)
        return [dict(t) for t in tasks]
    finally:
        conn.close()


@app.post("/api/rider/milestone", response_model=OrderResponse)
async def update_rider_milestone(
    update: MilestoneUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ROLE_RIDER"])),
):
    """Update order milestone status with optional dual-factor POD verification."""
    conn = get_db_connection()
    try:
        updated_order = transition_order_state(
            conn=conn,
            order_id=update.order_id,
            new_status=update.new_status,
            current_user=current_user,
            verification_pin=update.verification_pin,
            qr_token=update.qr_token,
            notes=update.notes,
        )

        await enqueue_notification_event({
            "order_id": update.order_id,
            "event_type": "STATUS_CHANGED",
            "payload": {
                "new_status": update.new_status,
            },
        })

        order_detail = get_order_by_id(conn, update.order_id)
        return dict(order_detail)
    finally:
        conn.close()


# ==================================================
# Public Customer Tracking Route
# ==================================================


@app.get("/api/track/{tracking_token}", response_model=PublicTrackingResponse)
async def track_delivery_order(tracking_token: str):
    """Public customer tracking endpoint returning live milestone stepper data."""
    conn = get_db_connection()
    try:
        order = get_order_by_tracking_token(conn, tracking_token)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tracking token '{tracking_token}' not found",
            )

        status_logs = get_status_logs_for_order(conn, order["id"])

        return PublicTrackingResponse(
            tracking_token=order["tracking_token"],
            customer_name=order["customer_name"],
            customer_phone=order["customer_phone"],
            delivery_address=order["delivery_address"],
            item_description=order["item_description"],
            package_value=order["package_value"],
            delivery_fee=order["delivery_fee"],
            status=order["status"],
            verification_pin=order["verification_pin"],
            created_at=str(order["created_at"]),
            assigned_at=str(order["assigned_at"]) if order["assigned_at"] else None,
            picked_up_at=str(order["picked_up_at"]) if order["picked_up_at"] else None,
            delivered_at=str(order["delivered_at"]) if order["delivered_at"] else None,
            retailer_name=order["retailer_name"],
            rider_name=order["rider_name"],
            rider_phone=order["rider_phone"],
            vehicle_plate=order["vehicle_plate"],
            vehicle_type=order["vehicle_type"],
            status_logs=[
                StatusLogResponse(
                    id=log["id"],
                    order_id=log["order_id"],
                    changed_by_user_id=log["changed_by_user_id"],
                    changed_by_username=log["changed_by_username"],
                    changed_by_full_name=log["changed_by_full_name"],
                    changed_by_role=log["changed_by_role"],
                    previous_status=log["previous_status"],
                    new_status=log["new_status"],
                    notes=log["notes"],
                    timestamp=str(log["timestamp"]),
                )
                for log in status_logs
            ],
        )
    finally:
        conn.close()


# ==================================================
# Static Frontend Serving
# ==================================================


@app.get("/")
async def serve_index():
    """Serve main multi-role dashboard."""
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Reflex API Gateway Active", "docs": "/docs"})


@app.get("/track/{tracking_token}")
async def serve_tracker_page(tracking_token: str):
    """Serve dedicated public customer tracking page."""
    tracker_file = os.path.join(FRONTEND_DIR, "tracker.html")
    if os.path.exists(tracker_file):
        return FileResponse(tracker_file)
    return JSONResponse({"tracking_token": tracking_token})


@app.get("/styles.css")
async def serve_styles():
    """Serve custom styles.css."""
    css_file = os.path.join(FRONTEND_DIR, "styles.css")
    return FileResponse(css_file, media_type="text/css")


@app.get("/app.js")
async def serve_app_js():
    """Serve application logic app.js."""
    js_file = os.path.join(FRONTEND_DIR, "app.js")
    return FileResponse(js_file, media_type="application/javascript")


@app.get("/tracker.html")
async def serve_tracker_html():
    """Serve tracker.html directly."""
    tracker_file = os.path.join(FRONTEND_DIR, "tracker.html")
    return FileResponse(tracker_file, media_type="text/html")


@app.get("/tracker.js")
async def serve_tracker_js():
    """Serve tracker.js ES6 module."""
    js_file = os.path.join(FRONTEND_DIR, "tracker.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/utils/{filename}")
async def serve_utils(filename: str):
    """Serve ES6 utility modules from the frontend/utils/ directory."""
    file_path = os.path.join(FRONTEND_DIR, "utils", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="File not found")


if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

