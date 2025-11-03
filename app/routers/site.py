from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Product
from app.db.session import get_db


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow

router = APIRouter(tags=["Site"])


def _serialize_product(product: Product) -> dict:
    primary_image = None
    gallery: list[dict] = []
    if product.images:
        sorted_images = sorted(product.images, key=lambda image: image.sort_order)
        primary_image = {
            "url": sorted_images[0].image_url,
            "alt": sorted_images[0].alt_text or product.name,
        }
        gallery = [
            {
                "url": image.image_url,
                "alt": image.alt_text or product.name,
            }
            for image in sorted_images
        ]

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "oem_number": product.oem_number,
        "summary": product.summary or "",
        "primary_image": primary_image,
        "images": gallery,
        "category": product.category.name if product.category else None,
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    stmt = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
        .limit(6)
    )
    products = db.execute(stmt).scalars().all()
    serialized_products = [_serialize_product(product) for product in products]

    context = {
        "request": request,
        "page": "home",
        "recent_products": serialized_products[:3],
        "featured_products": serialized_products,
    }
    return templates.TemplateResponse("site/home.html", context)


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("site/about.html", {"request": request, "page": "about"})


@router.get("/catalog", response_class=HTMLResponse)
def catalog(request: Request, db: Session = Depends(get_db)):
    products_stmt = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
    )
    products = db.execute(products_stmt).scalars().all()
    serialized_products = [_serialize_product(product) for product in products]

    categories_stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.name.asc())
    )
    categories = db.execute(categories_stmt).scalars().all()
    serialized_categories = [
        {"id": category.id, "name": category.name, "slug": category.slug}
        for category in categories
    ]

    context = {
        "request": request,
        "page": "catalog",
        "products": serialized_products,
        "categories": serialized_categories,
    }
    return templates.TemplateResponse("site/catalog.html", context)


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("site/contact.html", {"request": request, "page": "contact"})
