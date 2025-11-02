from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "page": "login"})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "page": "dashboard"})


@router.get("/products", response_class=HTMLResponse)
def manage_products(request: Request):
    return templates.TemplateResponse("admin/products.html", {"request": request, "page": "products"})


@router.get("/categories", response_class=HTMLResponse)
def manage_categories(request: Request):
    return templates.TemplateResponse("admin/categories.html", {"request": request, "page": "categories"})
