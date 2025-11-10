# NovaCommerce Starter

A FastAPI-powered foundation for a modern product catalog experience. This starter provides marketing-facing pages, a catalog layout, and an admin interface scaffolded for future integration with real data and authentication.

## Getting started

### Requirements
- Python 3.11+
- PostgreSQL 14+ (or a compatible managed instance)

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file to override configuration as needed (all values shown here are examples):

```
DATABASE_URL=postgresql+psycopg2://catalog_user:catalog_pass@localhost:5432/catalog
SECRET_KEY=please-generate-a-very-long-random-string-here
SESSION_COOKIE_NAME=admin_session
SESSION_COOKIE_SECURE=false  # set to true in production
SESSION_COOKIE_MAX_AGE=14400
SESSION_COOKIE_SAME_SITE=lax
```

### Bootstrapping the database

Once your environment variables are in place and the database server is reachable, run the bootstrap script to create tables and seed the initial admin account:

```bash
python scripts/bootstrap.py --email admin@example.com --full-name "Site Admin"
```

You can pass `--password` on the command line or leave it out to be prompted securely. Re-run the script later with the same email to update the admin profile or rotate the password. Add `--skip-tables` if the schema already exists.

### Running the application

```bash
uvicorn app.main:app --reload
```

The site pages are available at `http://localhost:8000` and the admin routes under `http://localhost:8000/admin`.

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

## Next steps
- Implement authentication and authorization for the admin workspace
- Wire templates to database-backed CRUD endpoints
- Add API schemas and client-side interactivity for catalog filtering
- Introduce automated tests and CI workflows

## Deployment readiness checklist
- [ ] Replace the placeholder `SECRET_KEY`, database URL, and session cookie name in `app/core/config.py` with environment variables specific to each server, and lock down `SessionMiddleware` cookies (`secure`, `httponly`, `max_age`, `same_site`).
- [ ] Decide on a single PostgreSQL driver (`psycopg` _or_ `psycopg2`), update `requirements.txt`, and verify dependency installation in the production environment.
- [ ] Document the production process manager (e.g., systemd, Supervisor, Docker) and how to run Uvicorn/Gunicorn when the site is deployed over FTP.
- [ ] Introduce Alembic migrations instead of relying on `Base.metadata.create_all()` in `scripts/bootstrap.py`, so future schema changes do not require manual intervention.
- [ ] Fix the bootstrap docs/CLI mismatch by supporting an `--email` (or updating the README to reflect `--uname`) and clearly explaining how initial admin credentials are created.
- [ ] Seed baseline catalog/category data (plus hosted product imagery) so the public pages are not empty immediately after deployment.
- [ ] Harden the admin experience: add CSRF protection, rate limiting, logging, and a password-reset flow to the `/admin/login` workflow.
- [ ] Make dashboard metrics, catalog/category search boxes, and status pills reflect real database queries (instead of static placeholders).
- [ ] Enhance category/product management: allow re-parenting, expose `is_active` toggles, add an image uploader, and ensure deletion flows redirect back to the relevant listing with confirmations.
- [ ] Implement functional catalog filters, hook up the homepage hero search, and send the contact form data to an email/service endpoint.
- [ ] Create the supporting marketing/legal pages referenced in the footer (privacy, terms, 404, robots.txt) and add monitoring/alerting guidance for `/health`.
