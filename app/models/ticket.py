"""Data access layer for tickets and notes.

Keeping every Mongo query in this module (instead of scattered across
routes) means the API blueprint and the Jinja2 view blueprint can both
call the same functions and always see the same shape of data.
"""

import re
from datetime import datetime, timezone

import app as app_module

VALID_STATUSES = ["Open", "In Progress", "Closed"]


def _db():
    # Fetched lazily (not at import time) because app.db is only set
    # once init_db() runs inside create_app().
    return app_module.db


def _now():
    return datetime.now(timezone.utc)


def _next_ticket_id():
    """Atomically increment a counter doc to get a gap-free sequence
    number, then format it as TKT-001, TKT-002, ... This is safe under
    concurrent requests because findAndModify/find_one_and_update is a
    single atomic operation in MongoDB - two simultaneous ticket
    creations can never receive the same number."""
    counter = _db().counters.find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return f"TKT-{counter['seq']:03d}"


def _serialize(doc):
    """Strip Mongo's internal _id from API/template-facing dicts."""
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def create_ticket(customer_name, customer_email, subject, description):
    now = _now()
    ticket = {
        "ticket_id": _next_ticket_id(),
        "customer_name": customer_name.strip(),
        "customer_email": customer_email.strip(),
        "subject": subject.strip(),
        "description": description.strip(),
        "status": "Open",
        "created_at": now,
        "updated_at": now,
    }
    _db().tickets.insert_one(ticket)
    return _serialize(ticket)


def list_tickets(status=None, search=None):
    query = {}

    if status and status in VALID_STATUSES:
        query["status"] = status

    if search:
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"ticket_id": pattern},
            {"customer_name": pattern},
            {"customer_email": pattern},
            {"subject": pattern},
            {"description": pattern},
        ]

    cursor = _db().tickets.find(query).sort("created_at", -1)
    return [_serialize(t) for t in cursor]


def get_ticket(ticket_id):
    ticket = _db().tickets.find_one({"ticket_id": ticket_id})
    if not ticket:
        return None
    ticket = _serialize(ticket)
    ticket["notes"] = get_notes(ticket_id)
    return ticket


def update_ticket(ticket_id, status=None, note_text=None):
    ticket = _db().tickets.find_one({"ticket_id": ticket_id})
    if not ticket:
        return None

    update_fields = {"updated_at": _now()}

    if status:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        update_fields["status"] = status

    _db().tickets.update_one({"ticket_id": ticket_id}, {"$set": update_fields})

    if note_text and note_text.strip():
        add_note(ticket_id, note_text.strip())

    return get_ticket(ticket_id)


def add_note(ticket_id, note_text):
    note = {
        "ticket_id": ticket_id,
        "note_text": note_text,
        "created_at": _now(),
    }
    _db().notes.insert_one(note)
    return _serialize(note)


def get_notes(ticket_id):
    cursor = _db().notes.find({"ticket_id": ticket_id}).sort("created_at", 1)
    return [_serialize(n) for n in cursor]


def ticket_counts_by_status():
    """Used by the dashboard header to show quick counts per status."""
    counts = {status: 0 for status in VALID_STATUSES}
    for status in VALID_STATUSES:
        counts[status] = _db().tickets.count_documents({"status": status})
    counts["All"] = sum(counts.values())
    return counts
