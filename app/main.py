from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import TemplateResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routers import admin, site

settings = get_settings()
configure_logging(settings.log_level)

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
        return TemplateResponse("site/404.html", {"request": request, "page": "404"}, status_code=404)
    raise exc
