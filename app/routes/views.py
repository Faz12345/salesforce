import re

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from pymongo.errors import DuplicateKeyError

from app import auth
from app import mailer
from app.models import user as user_model
from app.models import ticket as ticket_model

views_bp = Blueprint("views", __name__)


def _require_user():
    if not auth.get_request_user():
        return redirect(url_for("views.login", next=request.path))
    return None


@views_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = user_model.authenticate(request.form.get("email"), request.form.get("password"))
        if not user:
            return render_template("login.html", error="Invalid email or password."), 401
        response = redirect(request.form.get("next") or url_for("views.index"))
        token = auth.issue_access_token(user)
        response.set_cookie("access_token", token, httponly=True, secure=current_app.config["SESSION_COOKIE_SECURE"], samesite="Lax", max_age=current_app.config["JWT_ACCESS_MINUTES"] * 60)
        return response
    return render_template("login.html", next=request.args.get("next", ""))


@views_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = user_model.normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(password) < 8:
            return render_template("signup.html", error="Enter a name, valid email, and password of at least 8 characters."), 400
        try:
            user = user_model.create_user(email, password, name)
        except DuplicateKeyError:
            return render_template("signup.html", error="That email is already registered."), 409
        response = redirect(url_for("views.index"))
        response.set_cookie("access_token", auth.issue_access_token(user), httponly=True, secure=current_app.config["SESSION_COOKIE_SECURE"], samesite="Lax", max_age=current_app.config["JWT_ACCESS_MINUTES"] * 60)
        return response
    return render_template("signup.html")


@views_bp.get("/logout")
def logout():
    response = redirect(url_for("views.login"))
    response.delete_cookie("access_token")
    return response


@views_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None
    reset_token = None
    if request.method == "POST":
        user = user_model.find_auth_by_email(request.form.get("email"))
        if user and user.get("is_active"):
            reset_token = user_model.create_reset_token(user["user_id"])
            mailer.send_password_reset_email(user["email"], reset_token)
            if not current_app.config["EXPOSE_RESET_TOKEN"] or mailer.is_configured():
                reset_token = None
        message = "If that email exists, a reset link has been sent."
    return render_template("forgot_password.html", message=message, reset_token=reset_token)


@views_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    error = None
    if request.method == "POST":
        reset = user_model.consume_reset_token(request.form.get("token"))
        password = request.form.get("password", "")
        if not reset or len(password) < 8:
            error = "The reset token is invalid or expired, or the password is too short."
        else:
            user_model.set_password(reset["user_id"], password)
            flash("Password reset. Please log in.", "success")
            return redirect(url_for("views.login"))
    return render_template("reset_password.html", error=error, token=request.args.get("token", ""))


@views_bp.get("/")
def index():
    required = _require_user()
    if required:
        return required
    status = request.args.get("status") or None
    search = request.args.get("search") or None

    tickets = ticket_model.list_tickets(status=status, search=search)
    counts = ticket_model.ticket_counts_by_status()

    return render_template(
        "index.html",
        tickets=tickets,
        counts=counts,
        active_status=status or "All",
        search=search or "",
        statuses=ticket_model.VALID_STATUSES,
    )


@views_bp.route("/tickets/new", methods=["GET", "POST"])
def new_ticket():
    required = _require_user()
    if required:
        return required
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if not customer_name:
            errors.append("Customer name is required.")
        if not customer_email:
            errors.append("Customer email is required.")
        if not subject:
            errors.append("Issue title is required.")
        if not description:
            errors.append("Description is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("create.html", form=request.form), 400

        ticket = ticket_model.create_ticket(customer_name, customer_email, subject, description)
        flash(f"Ticket {ticket['ticket_id']} created.", "success")
        return redirect(url_for("views.ticket_detail", ticket_id=ticket["ticket_id"]))

    return render_template("create.html", form={})


@views_bp.get("/tickets/<ticket_id>")
def ticket_detail(ticket_id):
    required = _require_user()
    if required:
        return required
    ticket = ticket_model.get_ticket(ticket_id)
    if not ticket:
        abort(404)
    return render_template("detail.html", ticket=ticket, statuses=ticket_model.VALID_STATUSES)


@views_bp.post("/tickets/<ticket_id>/update")
def update_ticket_form(ticket_id):
    """Non-JS fallback for the detail page's status/notes form; the
    same data path (app/models/ticket.py) backs both this and the
    PUT /api/tickets/<id> endpoint used by fetch()."""
    required = _require_user()
    if required:
        return required
    if g.current_user.get("role") != "admin":
        abort(403)
    status = request.form.get("status")
    notes = request.form.get("notes")

    try:
        updated = ticket_model.update_ticket(ticket_id, status=status, note_text=notes)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("views.ticket_detail", ticket_id=ticket_id))

    if not updated:
        abort(404)

    flash("Ticket updated.", "success")
    return redirect(url_for("views.ticket_detail", ticket_id=ticket_id))


@views_bp.route("/profile", methods=["GET", "POST"])
def profile():
    required = _require_user()
    if required:
        return required
    if request.method == "POST":
        if g.current_user.get("role") != "admin":
            abort(403)
        try:
            user_model.update_profile(g.current_user["user_id"], name=request.form.get("name"), email=request.form.get("email"))
            flash("Profile updated.", "success")
        except DuplicateKeyError:
            flash("That email is already registered.", "error")
    user = user_model.find_by_id(g.current_user["user_id"])
    return render_template("profile.html", user=user)


@views_bp.get("/admin/users")
def admin_users():
    required = _require_user()
    if required:
        return required
    if g.current_user.get("role") != "admin":
        abort(403)
    return render_template("admin_users.html", users=user_model.list_users())


@views_bp.app_errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404
