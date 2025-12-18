# NovaCommerce Starter

A FastAPI-powered foundation for a modern product catalog experience. This starter provides marketing-facing pages, a catalog layout, and an admin interface scaffolded for future integration with real data and authentication.

## Getting started

### Requirements
- Python 3.11+
- MySQL 8.0+ (or a compatible managed instance)

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate a strong `SECRET_KEY` (at least 32 characters; 64+ recommended) and create a `.env` file to override configuration as needed. Example command to generate a key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Sample `.env` (all values shown here are examples):

```
DATABASE_URL=mysql+pymysql://catalog_user:catalog_pass@localhost:3306/catalog?charset=utf8mb4
SECRET_KEY=please-generate-a-very-long-random-string-here
SESSION_COOKIE_NAME=admin_session
SESSION_COOKIE_SECURE=false  # set to true in production
SESSION_COOKIE_MAX_AGE=14400
SESSION_COOKIE_SAME_SITE=lax
LOG_LEVEL=INFO
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
LOGIN_RATE_LIMIT_MAX_ATTEMPTS=5
# Email (optional, enables notifications)
SMTP_HOST=smtp.mailprovider.com
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=super-secret
SMTP_SENDER=notifications@example.com
NOTIFICATION_EMAIL=leads@example.com
SMTP_USE_TLS=true
```

### Bootstrapping the database

Once your environment variables are in place and the database server is reachable, run the bootstrap script to create tables, apply lightweight migrations (e.g., analytics counters), and seed the initial admin account:

```bash
python scripts/bootstrap.py --uname admin@example.com --full-name "Site Admin"
```

You can pass `--password` on the command line or leave it out to be prompted securely. Re-run the script any time to pick up new schema changes (safe for existing data) or with the same email to update the admin profile or rotate the password. Add `--skip-tables` if the schema already exists.

> Tip: The script adjusts `sys.path`, so you can run it from the repo root (`python scripts/bootstrap.py ...`) without needing to move it into repo root.

### Database migrations (Alembic)

Alembic is configured in `alembic.ini` with metadata in `alembic/env.py`.

- New database: `alembic upgrade head` (creates all tables), then run the bootstrap script to seed the admin account.
- Existing database with no Alembic history: `alembic stamp head` once, then `alembic upgrade head`.
- Creating a new migration after model changes: `alembic revision --autogenerate -m "describe change"` then `alembic upgrade head`.
- If you see a missing `script.py.mako` error, ensure the repository contains `alembic/script.py.mako` (included here) and that `alembic.ini` points to `script_location = alembic`.

### Running the application

```bash
uvicorn app.main:app --reload
```

The site pages are available at `http://localhost:8000` and the admin routes under `http://localhost:8000/admin`.

Notifications: if SMTP settings are provided, contact and quote requests will send emails to `NOTIFICATION_EMAIL` (or `SMTP_SENDER` as a fallback) and a confirmation to the requester.

Admin import/export: in the admin Products page you can download an Excel template, import products (name, SKU, OEM, category path, summary, active), and export current products as .xlsx. Images are still managed via the product editor.

### Deploying to a server (example)

Prereqs: Python 3.11+, MySQL reachable (or your chosen SQL backend), and a process manager (systemd shown below).

1) Copy the project to the server and set up a virtualenv:
```bash
python -m venv /opt/novacommerce/.venv
source /opt/novacommerce/.venv/bin/activate
pip install -r /opt/novacommerce/requirements.txt
```

2) Configure environment (`/opt/novacommerce/.env`) with `DATABASE_URL`, `SECRET_KEY`, SMTP settings, etc.

3) Run migrations and bootstrap:
```bash
cd /opt/novacommerce
alembic upgrade head
python scripts/bootstrap.py --uname admin@example.com --full-name "Site Admin"
```

4) Create a systemd unit (`/etc/systemd/system/novacommerce.service`):
```
[Unit]
Description=NovaCommerce FastAPI app
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/novacommerce
EnvironmentFile=/opt/novacommerce/.env
ExecStart=/opt/novacommerce/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

5) Start and enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now novacommerce
```

6) Put Nginx (or your preferred proxy) in front to serve TLS and proxy to `localhost:8000`. Example Nginx server block:
```
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /opt/novacommerce/app/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

7) Health check: GET `/health` should return `{"status": "ok"}`. Add it to your monitoring.

## Project structure

```
app/
  core/          # Configuration and settings modules
  db/            # Database models and session handling
  routers/       # FastAPI routers for site and admin areas
  static/        # Shared static assets (CSS, fonts, icons)
  templates/     # Jinja templates for pages and layouts
requirements.txt
```

## Included experience
- Hero landing page with brand messaging, primary search input, and automatic "recent products" slider.
- Marketing pages covering Home, About, Catalog, and Contact experiences that share a unified layout.
- Hoverable navigation cart preview showing selected items plus quote-ready actions.
- Marketing, catalog, and admin templates wired for future dynamic data without exposing pricing details.

## Project status

### Completed
- Secure FastAPI foundation with session middleware, CSRF protection, rate limiting, and structured logging for the admin workspace.
- Catalog, category, and dashboard pages already pull from the live SQLAlchemy models so marketing, catalog, and admin templates stay in sync with real data.
- Product management workflows (including image uploads, sorting, and recent-activity summaries) are live in the admin area.

### Needs work
- Automated tests/CI have not been set up, so schema changes and regressions are risky.
- A documented manual admin credential recovery process still needs to be resolved.
- Catalog UX gaps remain: expose `is_active` toggles and deletion redirects, wire the homepage hero search, make catalog filters interactive, and actually deliver contact form submissions.

## Next steps
- Document how to run Uvicorn/Gunicorn under the production process manager (systemd/Supervisor/Docker) and describe `/health` monitoring hooks.
- Add automated tests/CI so schema changes are tracked and verified.
- Describe the manual admin credential recovery procedure.
- Finish the remaining catalog UX: functional filters + hero search, contact form delivery to an email/service, admin `is_active` toggles, and friendly deletion redirects.

## Deployment readiness checklist
- [x] Replace the placeholder `SECRET_KEY`, database URL, and session cookie name in `app/core/config.py` with environment variables specific to each server, and lock down `SessionMiddleware` cookies (`secure`, `httponly`, `max_age`, `same_site`).
- [x] Decide on a single database driver (e.g., `pymysql` for MySQL, or `psycopg`/`psycopg2` for Postgres), update `requirements.txt`, and verify dependency installation in the production environment.
- [ ] Document the production process manager (e.g., systemd, Supervisor, Docker) and how to run Uvicorn/Gunicorn when the site is deployed over FTP.
- [x] Introduce Alembic migrations instead of relying on `Base.metadata.create_all()` in `scripts/bootstrap.py`, so future schema changes do not require manual intervention.
- [x] Fix the bootstrap docs/CLI mismatch by supporting an `--email` (or updating the README to reflect `--uname`) and clearly explaining how initial admin credentials are created.
- [x] Seed baseline catalog/category data (plus hosted product imagery) so the public pages are not empty immediately after deployment. _(Deferred to live admins who will manage content post-launch.)_
- [x] Harden the admin experience: add CSRF protection, structured logging, and rate limiting for admin routes.
- [x] Make dashboard metrics, catalog/category search boxes, and status pills reflect real database queries (instead of static placeholders).
- [ ] Establish a manual admin credential recovery process (password resets must be coordinated directly with the developer/operator until an automated flow exists).
- [ ] Enhance category/product management: expose `is_active` toggles, keep the image uploader improvements, and ensure deletion flows redirect back to the relevant listing with confirmations. (Re-parenting is intentionally disallowed to avoid data integrity issues.)
- [ ] Implement functional catalog filters, hook up the homepage hero search, and send the contact form data to an email/service endpoint.
- [x] Create the supporting marketing/legal pages referenced in the footer (privacy, terms, 404, robots.txt) and add monitoring/alerting guidance for `/health`.
