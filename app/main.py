from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
from markupsafe import Markup
import markdown as md

from app.core.text import render_rich_text

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routers import admin, site

settings = get_settings()
configure_logging(settings.log_level)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow
templates.env.filters["markdown"] = lambda text: Markup(md.markdown(text or "", extensions=["extra", "sane_lists"]))
templates.env.filters["richtext"] = render_rich_text
templates.env.globals["static_version"] = settings.static_version

app = FastAPI(title=settings.project_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    same_site=settings.session_cookie_same_site,
    https_only=settings.session_cookie_secure,
    max_age=settings.session_cookie_max_age,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(site.router)
app.include_router(admin.router)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        cart_fallback = {"items": [], "total_items": 0, "has_items": False, "preview": []}
        context = {"request": request, "page": "404", "cart": cart_fallback}
        return templates.TemplateResponse("site/404.html", context, status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)
