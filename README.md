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

Create a `.env` file to override configuration as needed:

```
DATABASE_URL=postgresql+psycopg://catalog_user:catalog_pass@localhost:5432/catalog
```

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

## Next steps
- Implement authentication and authorization for the admin workspace
- Wire templates to database-backed CRUD endpoints
- Add API schemas and client-side interactivity for catalog filtering
- Introduce automated tests and CI workflows
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

Create a `.env` file to override configuration as needed:

```
DATABASE_URL=postgresql+psycopg://catalog_user:catalog_pass@localhost:5432/catalog
```

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
- Hoverable navigation cart preview showing selected items plus quote-ready actions.
- Marketing, catalog, and admin templates wired for future dynamic data without exposing pricing details.

## Next steps
- Implement authentication and authorization for the admin workspace
- Wire templates to database-backed CRUD endpoints
- Add API schemas and client-side interactivity for catalog filtering
- Introduce automated tests and CI workflows
