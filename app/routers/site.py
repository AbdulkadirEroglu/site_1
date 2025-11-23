import json
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.db.models import Category, Lead, Product, ProductImage, SiteMetric
from app.db.session import get_db


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["now"] = datetime.utcnow

router = APIRouter(tags=["Site"])
logger = logging.getLogger("app.site")
settings = get_settings()

CART_SESSION_KEY = "cart"
VISIT_SESSION_KEY = "site_visit_last_ts"
VISIT_WINDOW_SECONDS = 1800  # 30 minutes


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
        "created_at": product.created_at,
    }


def _normalize_cart(request: Request) -> dict[int, int]:
    raw_cart = request.session.get(CART_SESSION_KEY, {}) or {}
    normalized: dict[int, int] = {}
    for key, value in raw_cart.items():
        try:
            product_id = int(key)
            quantity = int(value)
        except (TypeError, ValueError):
            continue
        quantity = max(1, min(quantity, 99))
        normalized[product_id] = quantity

    request.session[CART_SESSION_KEY] = {str(pid): qty for pid, qty in normalized.items()}
    return normalized


def _cart_context(request: Request, db: Session) -> dict:
    cart_map = _normalize_cart(request)
    if not cart_map:
        return {"cart": {"items": [], "total_items": 0, "has_items": False, "preview": []}}

    products = (
        db.execute(select(Product).where(Product.id.in_(cart_map.keys()), Product.is_active.is_(True)))
        .scalars()
        .unique()
        .all()
    )
    product_map = {product.id: product for product in products}

    items: list[dict] = []
    for product_id, quantity in cart_map.items():
        product = product_map.get(product_id)
        if not product:
            continue
        serialized = _serialize_product(product)
        serialized["quantity"] = quantity
        items.append(serialized)

    total_items = sum(item["quantity"] for item in items)
    return {
        "cart": {
            "items": items,
            "total_items": total_items,
            "has_items": total_items > 0,
            "preview": items[:3],
        }
    }


def _safe_redirect_target(redirect_to: Optional[str], request: Request) -> str:
    if redirect_to:
        parsed = urlparse(redirect_to)
        if not parsed.netloc and redirect_to.startswith("/"):
            return redirect_to
        if parsed.netloc == request.url.hostname and parsed.path:
            path = parsed.path
            if parsed.query:
                path = f"{path}?{parsed.query}"
            return path
    referer = request.headers.get("referer")
    if referer:
        parsed_referer = urlparse(referer)
        if parsed_referer.netloc in ("", request.url.hostname):
            path = parsed_referer.path or "/"
            if parsed_referer.query:
                path = f"{path}?{parsed_referer.query}"
            return path
    return "/"


def _bump_metric(db: Session, *, key: str, amount: int = 1) -> None:
    metric = db.scalar(select(SiteMetric).where(SiteMetric.key == key))
    if not metric:
        metric = SiteMetric(key=key, value=0)
        db.add(metric)
    metric.value += amount
    db.commit()


def _increment_product_views(db: Session, product: Product) -> None:
    product.view_count = (product.view_count or 0) + 1
    if product.category:
        product.category.view_count = (product.category.view_count or 0) + 1
    _bump_metric(db, key="site_product_views", amount=1)


def _increment_cart_adds(db: Session, product: Product) -> None:
    product.cart_add_count = (product.cart_add_count or 0) + 1
    if product.category:
        product.category.cart_add_count = (product.category.cart_add_count or 0) + 1
    _bump_metric(db, key="site_cart_adds", amount=1)


def _track_visit(request: Request, db: Session) -> None:
    """Count a site visit once per session window to avoid over-counting navigation."""
    now_ts = datetime.utcnow().timestamp()
    last_visit_ts = request.session.get(VISIT_SESSION_KEY)
    if last_visit_ts and isinstance(last_visit_ts, (int, float)):
        if now_ts - last_visit_ts < VISIT_WINDOW_SECONDS:
            return
    _bump_metric(db, key="site_visits", amount=1)
    request.session[VISIT_SESSION_KEY] = now_ts


def _notification_recipients() -> list[str]:
    recipients: list[str] = []
    if settings.notification_email:
        recipients.append(settings.notification_email)
    elif settings.smtp_sender:
        recipients.append(settings.smtp_sender)
    return recipients


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    _track_visit(request, db)

    newest_stmt = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
        .limit(6)
    )
    newest_products = db.execute(newest_stmt).scalars().all()

    popular_stmt = (
        select(Product)
        .outerjoin(ProductImage)
        .where(Product.is_active.is_(True))
        .group_by(Product.id)
        .order_by(func.count(ProductImage.id).desc(), Product.created_at.desc())
        .limit(6)
    )
    popular_products = db.execute(popular_stmt).scalars().unique().all()

    serialized_newest = [_serialize_product(product) for product in newest_products]
    serialized_popular = [_serialize_product(product) for product in popular_products]

    context = {
        "request": request,
        "page": "home",
        "new_products": serialized_newest,
        "popular_products": serialized_popular or serialized_newest,
    }
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/home.html", context)


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    context = {"request": request, "page": "about"}
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/about.html", context)


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, db: Session = Depends(get_db)):
    context = {"request": request, "page": "privacy"}
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/privacy.html", context)


@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request, db: Session = Depends(get_db)):
    context = {"request": request, "page": "terms"}
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/terms.html", context)


@router.get("/catalog", response_class=HTMLResponse)
def catalog(
    request: Request,
    q: str = Query("", alias="q"),
    category: str = Query("", alias="category"),
    oem: str = Query("", alias="oem"),
    db: Session = Depends(get_db),
):
    _track_visit(request, db)

    filters = {
        "q": q.strip(),
        "category": category.strip(),
        "oem": oem.strip(),
    }
    products_stmt = (
        select(Product)
        .outerjoin(Category)
        .where(Product.is_active.is_(True))
    )
    if filters["q"]:
        pattern = f"%{filters['q']}%"
        products_stmt = products_stmt.where(
            or_(
                Product.name.ilike(pattern),
                Product.summary.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.oem_number.ilike(pattern),
            )
        )
    if filters["category"]:
        products_stmt = products_stmt.where(Category.slug == filters["category"])
    if filters["oem"]:
        products_stmt = products_stmt.where(Product.oem_number.ilike(f"%{filters['oem']}%"))

    products_stmt = products_stmt.order_by(Product.created_at.desc())
    products = db.execute(products_stmt).scalars().unique().all()
    serialized_products = [_serialize_product(product) for product in products]
    has_filters = any(filters.values())

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
        "filters": {**filters, "has_active": has_filters},
    }
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/catalog.html", context)


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    _track_visit(request, db)
    _increment_product_views(db, product)

    serialized_product = _serialize_product(product)

    related_products_stmt = (
        select(Product)
        .where(Product.is_active.is_(True), Product.id != product.id)
        .order_by(Product.created_at.desc())
        .limit(4)
    )
    if product.category_id:
        related_products_stmt = related_products_stmt.where(Product.category_id == product.category_id)
    related_products = db.execute(related_products_stmt).scalars().unique().all()
    serialized_related = [_serialize_product(related) for related in related_products]

    context = {
        "request": request,
        "page": "product",
        "product": serialized_product,
        "related_products": serialized_related,
    }
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/product_detail.html", context)


@router.get("/cart", response_class=HTMLResponse)
def cart_page(
    request: Request,
    submitted: bool = Query(False, alias="submitted"),
    db: Session = Depends(get_db),
):
    context = {
        "request": request,
        "page": "cart",
        "submitted": submitted,
    }
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/cart.html", context)


@router.post("/cart/add")
def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(1),
    redirect_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = _normalize_cart(request)
    safe_quantity = max(1, min(quantity, 99))
    cart[product_id] = cart.get(product_id, 0) + safe_quantity
    _increment_cart_adds(db, product)
    db.commit()
    request.session[CART_SESSION_KEY] = {str(pid): qty for pid, qty in cart.items()}

    target = _safe_redirect_target(redirect_to, request)
    return RedirectResponse(target, status_code=303)


@router.post("/cart/remove")
def remove_from_cart(
    request: Request,
    product_id: int = Form(...),
    redirect_to: str | None = Form(None),
):
    cart = _normalize_cart(request)
    cart.pop(product_id, None)
    request.session[CART_SESSION_KEY] = {str(pid): qty for pid, qty in cart.items()}
    target = _safe_redirect_target(redirect_to, request)
    return RedirectResponse(target, status_code=303)


@router.post("/cart/clear")
def clear_cart(request: Request, redirect_to: str | None = Form(None)):
    request.session[CART_SESSION_KEY] = {}
    target = _safe_redirect_target(redirect_to, request)
    return RedirectResponse(target, status_code=303)


@router.post("/cart/request-quote")
def request_quote(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    cart = _normalize_cart(request)
    if not cart:
        return RedirectResponse("/cart", status_code=303)

    payload = {
        "cart_items": [{"product_id": pid, "quantity": qty} for pid, qty in cart.items()],
        "notes": notes,
    }
    lead = Lead(
        kind="quote",
        full_name=full_name.strip(),
        email=email.strip(),
        company=company.strip(),
        message=notes.strip(),
        payload=json.dumps(payload),
    )
    db.add(lead)
    db.commit()

    notify_recipients = _notification_recipients()
    if notify_recipients:
        send_email(
            subject=f"New quote request from {full_name}",
            body=(
                f"Name: {full_name}\nEmail: {email}\nCompany: {company}\n"
                f"Items: {payload['cart_items']}\nNotes:\n{notes}"
            ),
            to=notify_recipients,
        )
    if email:
        send_email(
            subject="We received your quote request",
            body="Thanks for requesting a quote. We'll reply with pricing and timelines shortly.",
            to=[email],
        )

    logger.info(
        "Quote requested",
        extra={
            "full_name": full_name,
            "email": email,
            "company": company,
            "notes": notes,
            "cart_item_ids": list(cart.keys()),
        },
    )
    request.session[CART_SESSION_KEY] = {}
    return RedirectResponse("/cart?submitted=true", status_code=303)


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request, db: Session = Depends(get_db)):
    submitted = request.query_params.get("submitted") == "true"
    context = {"request": request, "page": "contact", "submitted": submitted}
    context.update(_cart_context(request, db))
    return templates.TemplateResponse("site/contact.html", context)


@router.post("/contact", response_class=HTMLResponse)
def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(""),
    company: str = Form(""),
    db: Session = Depends(get_db),
):
    lead = Lead(
        kind="contact",
        full_name=name.strip(),
        email=email.strip(),
        company=company.strip(),
        message=message.strip(),
    )
    db.add(lead)
    db.commit()
    notify_recipients = _notification_recipients()
    if notify_recipients:
        send_email(
            subject=f"New contact from {lead.full_name or 'Unknown'}",
            body=(
                f"Name: {lead.full_name}\nEmail: {lead.email}\nCompany: {lead.company}\n"
                f"Message:\n{lead.message}"
            ),
            to=notify_recipients,
        )
    if lead.email:
        send_email(
            subject="We received your message",
            body="Thanks for reaching out. Our team will follow up shortly.",
            to=[lead.email],
        )
    return RedirectResponse("/contact?submitted=true", status_code=303)


@router.get("/robots.txt")
def robots_txt(request: Request) -> Response:
    sitemap_url = request.url_for("sitemap")
    content = f"""User-agent: *
Allow: /
Sitemap: {sitemap_url}
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
def sitemap(request: Request, db: Session = Depends(get_db)) -> Response:
    pages = [
        request.url_for("home"),
        request.url_for("about"),
        request.url_for("catalog"),
        request.url_for("contact"),
        request.url_for("privacy"),
        request.url_for("terms"),
    ]
    products = db.execute(select(Product).where(Product.is_active.is_(True))).scalars().all()
    categories = db.execute(select(Category).where(Category.is_active.is_(True))).scalars().all()

    urls = []
    for page in pages:
        urls.append(f"<url><loc>{page}</loc></url>")
    for category in categories:
        loc = f"{request.url_for('catalog')}?category={category.slug}"
        urls.append(f"<url><loc>{loc}</loc></url>")
    for product in products:
        loc = request.url_for("product_detail", product_id=product.id)
        lastmod = product.updated_at.strftime("%Y-%m-%d") if product.updated_at else ""
        urls.append(f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
    xml += "".join(urls)
    xml += "</urlset>"
    return Response(content=xml, media_type="application/xml")
