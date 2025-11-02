from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow

router = APIRouter(tags=["Site"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("site/home.html", {"request": request, "page": "home"})


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("site/about.html", {"request": request, "page": "about"})


@router.get("/products", response_class=HTMLResponse)
def products(request: Request):
    return templates.TemplateResponse("site/products.html", {"request": request, "page": "products"})


@router.get("/catalog", response_class=HTMLResponse)
def catalog(request: Request):
    return templates.TemplateResponse("site/catalog.html", {"request": request, "page": "catalog"})


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("site/contact.html", {"request": request, "page": "contact"})
