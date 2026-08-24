from flask import Blueprint, jsonify, request

from app.auth import admin_required, jwt_required
from app.models import ticket as ticket_model

api_bp = Blueprint("api", __name__)


def _iso(dt):
    return dt.isoformat() if dt else None


@api_bp.post("/tickets")
@jwt_required
def create_ticket():
    data = request.get_json(silent=True) or {}

    required = ["customer_name", "customer_email", "subject", "description"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

    ticket = ticket_model.create_ticket(
        customer_name=data["customer_name"],
        customer_email=data["customer_email"],
        subject=data["subject"],
        description=data["description"],
    )
    return (
        jsonify({"ticket_id": ticket["ticket_id"], "created_at": _iso(ticket["created_at"])}),
        201,
    )


@api_bp.get("/tickets")
@jwt_required
def list_tickets():
    status = request.args.get("status")
    search = request.args.get("search")

    tickets = ticket_model.list_tickets(status=status, search=search)
    return jsonify(
        [
            {
                "ticket_id": t["ticket_id"],
                "customer_name": t["customer_name"],
                "subject": t["subject"],
                "status": t["status"],
                "created_at": _iso(t["created_at"]),
            }
            for t in tickets
        ]
    )


@api_bp.get("/tickets/<ticket_id>")
@jwt_required
def get_ticket(ticket_id):
    ticket = ticket_model.get_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify(
        {
            "ticket_id": ticket["ticket_id"],
            "customer_name": ticket["customer_name"],
            "customer_email": ticket["customer_email"],
            "subject": ticket["subject"],
            "description": ticket["description"],
            "status": ticket["status"],
            "created_at": _iso(ticket["created_at"]),
            "updated_at": _iso(ticket["updated_at"]),
            "notes": [
                {"note_text": n["note_text"], "created_at": _iso(n["created_at"])}
                for n in ticket["notes"]
            ],
        }
    )


@api_bp.put("/tickets/<ticket_id>")
@admin_required
def update_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    notes = data.get("notes")

    if status and status not in ticket_model.VALID_STATUSES:
        return (
            jsonify({"error": f"Invalid status. Must be one of {ticket_model.VALID_STATUSES}"}),
            400,
        )

    try:
        updated = ticket_model.update_ticket(ticket_id, status=status, note_text=notes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not updated:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify({"success": True, "updated_at": _iso(updated["updated_at"])})
