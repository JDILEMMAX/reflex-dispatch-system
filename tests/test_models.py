"""Validation tests for schema contracts used by cancellation and reassignment workflows."""

from backend.models import (
    CancellationNoteRequest,
    DispatcherReassignmentReason,
    OrderCancellationNote,
    ReassignmentReasonRequest,
)


def test_cancellation_note_schema_accepts_optional_note():
    """Cancellation note payload should validate and preserve human-readable context."""
    payload = OrderCancellationNote(order_id=42, note="Customer requested cancellation after duplicate order")
    assert payload.order_id == 42
    assert payload.note == "Customer requested cancellation after duplicate order"

    request = CancellationNoteRequest(order_id=7)
    assert request.order_id == 7
    assert request.note is None


def test_dispatcher_reassignment_reason_schema_requires_reason():
    """Reassignment payload should capture the dispatcher rationale and target rider."""
    payload = DispatcherReassignmentReason(
        order_id=9,
        current_rider_id=4,
        new_rider_id=8,
        reason="Rider is unavailable due to mechanical issue",
    )
    assert payload.current_rider_id == 4
    assert payload.new_rider_id == 8
    assert payload.reason == "Rider is unavailable due to mechanical issue"

    alias = ReassignmentReasonRequest(
        order_id=9,
        new_rider_id=8,
        reason="Route conflict requires reallocation",
    )
    assert alias.new_rider_id == 8
    assert alias.reason == "Route conflict requires reallocation"
