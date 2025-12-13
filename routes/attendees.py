from flask import Blueprint, request, jsonify
from extensions import db, limiter
from models import Attendee, Event
from services.email_service import send_rsvp_notification

bp = Blueprint("attendees", __name__, url_prefix="/api/attendees")


@bp.route("/rsvp", methods=["POST"])
@limiter.limit("5 per minute")  # Strict rate limit for RSVP
def create_rsvp():
    data = request.get_json()

    # Validate required fields
    required = ["event_slug", "whatsapp_number", "name", "num_adults"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    # Find event
    event = Event.query.filter_by(slug=data["event_slug"]).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check if already RSVP'd
    existing = Attendee.query.filter_by(
        event_id=event.id, whatsapp_number=data["whatsapp_number"]
    ).first()

    if existing:
        return jsonify({"error": "You have already RSVP'd to this event"}), 400

    # Create attendee
    attendee = Attendee(
        event_id=event.id,
        whatsapp_number=data["whatsapp_number"],
        name=data["name"],
        num_adults=data["num_adults"],
        num_children=data.get("num_children", 0),
        comments=data.get("comments", ""),
    )

    db.session.add(attendee)
    db.session.commit()

    # Send email to host
    send_rsvp_notification(event, attendee)

    return jsonify({"message": "RSVP successful", "attendee_id": attendee.id}), 201


@bp.route("/find", methods=["POST"])
def find_attendee():
    """Find attendee by WhatsApp number and event slug"""
    data = request.get_json()

    event_slug = data.get("event_slug")
    whatsapp_number = data.get("whatsapp_number")

    if not event_slug or not whatsapp_number:
        return jsonify({"error": "Event slug and WhatsApp number are required"}), 400

    # Find event
    event = Event.query.filter_by(slug=event_slug).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Find attendee
    attendee = Attendee.query.filter_by(
        event_id=event.id, whatsapp_number=whatsapp_number
    ).first()

    if not attendee:
        return jsonify({"error": "RSVP not found for this WhatsApp number"}), 404

    return (
        jsonify(
            {
                "attendee": {
                    "id": attendee.id,
                    "name": attendee.name,
                    "whatsapp_number": attendee.whatsapp_number,
                    "num_adults": attendee.num_adults,
                    "num_children": attendee.num_children,
                    "comments": attendee.comments,
                    "status": attendee.status,
                    "created_at": attendee.created_at.isoformat(),
                },
                "event": {
                    "title": event.title,
                    "event_date": event.event_date.isoformat(),
                    "allow_modifications": event.allow_modifications,
                    "allow_cancellations": event.allow_cancellations,
                },
            }
        ),
        200,
    )


@bp.route("/modify", methods=["PUT"])
def modify_rsvp():
    """Modify existing RSVP"""
    data = request.get_json()

    event_slug = data.get("event_slug")
    whatsapp_number = data.get("whatsapp_number")

    if not event_slug or not whatsapp_number:
        return jsonify({"error": "Event slug and WhatsApp number are required"}), 400

    # Find event
    event = Event.query.filter_by(slug=event_slug).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check if modifications are allowed
    if not event.allow_modifications:
        return jsonify({"error": "Modifications are not allowed for this event"}), 403

    # Find attendee
    attendee = Attendee.query.filter_by(
        event_id=event.id, whatsapp_number=whatsapp_number
    ).first()

    if not attendee:
        return jsonify({"error": "RSVP not found"}), 404

    # Update fields
    if "name" in data:
        attendee.name = data["name"]
    if "num_adults" in data:
        attendee.num_adults = data["num_adults"]
    if "num_children" in data:
        attendee.num_children = data["num_children"]
    if "comments" in data:
        attendee.comments = data["comments"]

    # If was cancelled, reactivate
    if attendee.status == "cancelled":
        attendee.status = "confirmed"

    db.session.commit()

    return (
        jsonify(
            {
                "message": "RSVP updated successfully",
                "attendee": {
                    "id": attendee.id,
                    "name": attendee.name,
                    "num_adults": attendee.num_adults,
                    "num_children": attendee.num_children,
                    "comments": attendee.comments,
                    "status": attendee.status,
                },
            }
        ),
        200,
    )


@bp.route("/cancel", methods=["POST"])
def cancel_rsvp():
    """Cancel existing RSVP"""
    data = request.get_json()

    event_slug = data.get("event_slug")
    whatsapp_number = data.get("whatsapp_number")

    if not event_slug or not whatsapp_number:
        return jsonify({"error": "Event slug and WhatsApp number are required"}), 400

    # Find event
    event = Event.query.filter_by(slug=event_slug).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    # Check if cancellations are allowed
    if not event.allow_cancellations:
        return jsonify({"error": "Cancellations are not allowed for this event"}), 403

    # Find attendee
    attendee = Attendee.query.filter_by(
        event_id=event.id, whatsapp_number=whatsapp_number
    ).first()

    if not attendee:
        return jsonify({"error": "RSVP not found"}), 404

    # Cancel RSVP
    attendee.status = "cancelled"
    db.session.commit()

    return jsonify({"message": "RSVP cancelled successfully"}), 200
