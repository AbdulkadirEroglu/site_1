from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.models import AdminUser
from app.db.session import get_db

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_admin_from_session(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get("admin_user_id")
    if not admin_id:
        return None

    admin = db.get(AdminUser, admin_id)
    if not admin or not admin.is_active:
        request.session.pop("admin_user_id", None)
        return None
    return admin


@router.get("/login", response_class=HTMLResponse)
def login(request: Request, db: Session = Depends(get_db)):
    if _get_admin_from_session(request, db):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "page": "login", "form_error": None},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    context = {"request": request, "page": "login", "form_error": None}

    normalized_username = username.strip()
    stmt = select(AdminUser).where(
        AdminUser.user_name == normalized_username,
        AdminUser.is_active.is_(True),
    )
    admin = db.execute(stmt).scalar_one_or_none()

    if not admin or not verify_password(password, admin.password_hash):
        context["form_error"] = "Invalid username or password."
        return templates.TemplateResponse("admin/login.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    request.session["admin_user_id"] = admin.id
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    request.session.pop("admin_user_id", None)
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_from_session(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "page": "dashboard", "admin": admin},
    )

@router.get("/products", response_class=HTMLResponse)
def manage_products(request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_from_session(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "admin/products.html",
        {"request": request, "page": "products", "admin": admin},
    )

@router.get("/categories", response_class=HTMLResponse)
def manage_categories(request: Request, db: Session = Depends(get_db)):
    admin = _get_admin_from_session(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "admin/categories.html",
        {"request": request, "page": "categories", "admin": admin},
    )
