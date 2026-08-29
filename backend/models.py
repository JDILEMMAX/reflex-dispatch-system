"""Pydantic data models and schemas for Reflex Delivery System."""

from typing import List, Optional
from pydantic import BaseModel, Field


# Authentication Models
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str
    user_id: int
    rider_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: str
    phone: str
    created_at: Optional[str] = None
    rider_id: Optional[int] = None
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None


# Order Models
class OrderCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, description="Destination recipient full name")
    customer_phone: str = Field(..., min_length=9, description="Recipient telephone number")
    delivery_address: str = Field(..., min_length=3, description="Street address and building details")
    item_description: str = Field(..., min_length=2, description="Parcel contents description")
    package_value: float = Field(default=0.0, ge=0, description="Declared commercial package value in KES")
    delivery_fee: float = Field(default=0.0, ge=0, description="Agreed courier fee in KES")


class StatusLogResponse(BaseModel):
    id: int
    order_id: int
    changed_by_user_id: int
    changed_by_username: Optional[str] = None
    changed_by_full_name: Optional[str] = None
    changed_by_role: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = None
    timestamp: str


class OrderResponse(BaseModel):
    id: int
    retailer_id: int
    rider_id: Optional[int] = None
    tracking_token: str
    customer_name: str
    customer_phone: str
    delivery_address: str
    item_description: str
    package_value: float
    delivery_fee: float
    status: str
    verification_pin: str
    created_at: str
    assigned_at: Optional[str] = None
    picked_up_at: Optional[str] = None
    delivered_at: Optional[str] = None
    retailer_name: Optional[str] = None
    retailer_phone: Optional[str] = None
    rider_name: Optional[str] = None
    rider_phone: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None


class AssignmentRequest(BaseModel):
    order_id: int
    rider_id: int


class MilestoneUpdateRequest(BaseModel):
    order_id: int
    new_status: str
    verification_pin: Optional[str] = None
    qr_token: Optional[str] = None
    notes: Optional[str] = None


class VerificationRequest(BaseModel):
    order_id: int
    verification_pin: Optional[str] = None
    qr_token: Optional[str] = None


class CancellationNoteRequest(BaseModel):
    """Optional note attached when a retailer or dispatcher cancels an order."""
    order_id: int = Field(..., gt=0, description="Delivery order ID being cancelled")
    note: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=500,
        description="Human-readable cancellation rationale or operational note",
    )


class OrderCancellationNote(CancellationNoteRequest):
    """A validated cancellation payload suitable for API requests and audit logs."""
    note: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Explicit reason or explanation for the cancellation",
    )


class ReassignmentReasonRequest(BaseModel):
    """Dispatcher reassignment payload noting the reason a rider must be replaced."""
    order_id: int = Field(..., gt=0, description="Delivery order ID being reassigned")
    new_rider_id: int = Field(..., gt=0, description="Replacement rider selected for the order")
    reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Dispatcher rationale for reassigning the order to another rider",
    )


class DispatcherReassignmentReason(ReassignmentReasonRequest):
    """Extended reassignment payload that includes the current rider context."""
    current_rider_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Current assigned rider being replaced",
    )


class PublicTrackingResponse(BaseModel):
    tracking_token: str
    customer_name: str
    customer_phone: Optional[str] = None
    delivery_address: str
    item_description: str
    package_value: float
    delivery_fee: float
    status: str
    verification_pin: str
    created_at: str
    assigned_at: Optional[str] = None
    picked_up_at: Optional[str] = None
    delivered_at: Optional[str] = None
    retailer_name: Optional[str] = None
    rider_name: Optional[str] = None
    rider_phone: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    status_logs: List[StatusLogResponse] = []


class RiderProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    vehicle_type: str
    vehicle_plate: str
    phone_number: str
    is_active: int
    active_tasks_count: int = 0
