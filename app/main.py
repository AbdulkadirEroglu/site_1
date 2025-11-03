from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.routers import admin, site

settings = get_settings()

app = FastAPI(title=settings.project_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(site.router)
app.include_router(admin.router)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
