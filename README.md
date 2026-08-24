# Dispatch — Support CRM

Dispatch is a full-stack customer support CRM for managing customer issues as support tickets. Support teams can log, search, review, and track tickets while administrators control team accounts and permissions.

Built with Flask, MongoDB, Jinja2, JWT authentication, and a responsive server-rendered web interface.

## Features

- Create support tickets with customer details, subject, and description
- Generate unique ticket IDs such as `TKT-001`
- Search tickets by ID, customer, email, subject, or description
- Filter tickets by `Open`, `In Progress`, or `Closed`
- Add notes and track ticket update timestamps
- User registration and login
- Stateless JWT authentication through Bearer tokens and secure cookies
- User profile viewing and administrator profile management
- User and admin roles
- Admin-only ticket updates and team-account management
- Password reset through SMTP email
- One-time, expiring, hashed password-reset tokens
- MongoDB Atlas, local MongoDB, or in-memory `mongomock` support

## User permissions

| Action | Regular user | Admin |
|---|---:|---:|
| View all tickets | Yes | Yes |
| Create tickets | Yes | Yes |
| Update ticket status or notes | No | Yes |
| View own profile | Yes | Yes |
| Edit profiles | No | Yes |
| Manage roles and account status | No | Yes |

## Technology stack

- **Backend:** Python, Flask 3
- **Database:** MongoDB with PyMongo
- **Authentication:** PyJWT and Werkzeug password hashing
- **Frontend:** Jinja2, HTML, CSS, vanilla JavaScript
- **Email:** SMTP with Gmail, SendGrid, Mailgun, or another SMTP provider
- **Deployment:** Gunicorn with Railway, Render, or another Python host

## Project structure

```text
run.py                       Application entry point
app/
  __init__.py                Flask app factory and database initialization
  auth.py                    JWT validation and role decorators
  config.py                  Environment-based configuration
  mailer.py                  SMTP password-reset email delivery
  models/
    ticket.py                Ticket and note data access
    user.py                  User and reset-token data access
  routes/
    api.py                   Ticket REST API
    auth.py                  Auth, profile, reset, and admin API
    views.py                 Browser pages and form handlers
templates/                   Jinja2 pages
static/                      CSS and JavaScript assets
Procfile                    Production Gunicorn command
```

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/Faz12345/CRM.git
cd CRM/support-crm
```

Adjust the final directory if your clone places the project files directly in the repository root.

### 2. Create and activate a virtual environment

Linux or WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually if `cp` is unavailable. Then set the required values. Never commit `.env` because it contains secrets.

For a quick local demo without MongoDB, use:

```dotenv
USE_MONGOMOCK=true
```

The mock database is in memory and data disappears when the process stops. For persistent data, use MongoDB Atlas or a local MongoDB server and set:

```dotenv
USE_MONGOMOCK=false
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=support_crm
```

### 5. Start the application

```bash
python run.py
```

Open <http://localhost:5000>.

## Browser pages

- `/login` — sign in
- `/signup` — create a regular user account
- `/logout` — sign out
- `/forgot-password` — request a reset email
- `/reset-password` — choose a new password
- `/` — ticket dashboard
- `/tickets/new` — create a ticket
- `/profile` — view the current profile
- `/admin/users` — admin-only team management

The first administrator can be created automatically on startup with:

```dotenv
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=use-a-strong-password
```

## API endpoints

Authentication returns a JWT access token. API clients should send it as:

```text
Authorization: Bearer <access-token>
```

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a regular user |
| `POST` | `/api/auth/login` | Log in and receive a JWT |
| `GET` | `/api/auth/me` | Get the current user |
| `PATCH` | `/api/auth/profile` | Update profile through the API |
| `POST` | `/api/auth/forgot-password` | Request a reset email |
| `POST` | `/api/auth/reset-password` | Consume a reset token |
| `GET` | `/api/auth/admin/users` | List users as an admin |
| `PATCH` | `/api/auth/admin/users/<user_id>` | Manage a user as an admin |

### Tickets

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/tickets` | Authenticated users |
| `GET` | `/api/tickets` | Authenticated users |
| `GET` | `/api/tickets/<ticket_id>` | Authenticated users |
| `PUT` | `/api/tickets/<ticket_id>` | Admins only |

## SMTP password recovery

The application sends password-reset emails through authenticated SMTP. Gmail users must enable 2-Step Verification and create a Google **App Password**. Do not use a normal Gmail password or a Google passkey for SMTP.

Example Gmail configuration:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-google-app-password
MAIL_FROM=your-email@gmail.com
APP_BASE_URL=http://localhost:5000
EXPOSE_RESET_TOKEN=false
```

For local testing without an SMTP provider, set `EXPOSE_RESET_TOKEN=true`. The reset token will then be shown by the local reset flow. Keep this disabled in production.

## Deployment

The included `Procfile` starts the application with Gunicorn:

```text
web: gunicorn run:app --bind 0.0.0.0:$PORT
```

For Railway, Render, or a similar host:

1. Push the repository to GitHub.
2. Create a web service from the repository.
3. Add the variables from `.env.example` in the host dashboard.
4. Use MongoDB Atlas or another accessible MongoDB instance.
5. Set `USE_MONGOMOCK=false`.
6. Set `SESSION_COOKIE_SECURE=true` when the site uses HTTPS.
7. Keep `EXPOSE_RESET_TOKEN=false`.

## Security notes

- Use long, unique values for `SECRET_KEY` and `JWT_SECRET_KEY`.
- Rotate any database or admin credentials that have been exposed.
- Never commit `.env`, passwords, SMTP credentials, or JWT secrets.
- Use a Google App Password rather than a Gmail account password.
- Use HTTPS in production.
- Reset tokens expire after one hour and are stored hashed.
- Password changes, role changes, and deactivated accounts invalidate older JWTs.

## License

This project is provided for learning, portfolio, and internal-use purposes. Add a project-specific license before distributing it publicly.
