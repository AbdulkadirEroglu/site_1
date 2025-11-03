import re
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.models import AdminUser, Category, Product, ProductImage
from app.db.session import get_db

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_admin_from_session(request: Request, db: Session) -> Optional[AdminUser]:
    admin_id = request.session.get("admin_user_id")
    if not admin_id:
        return None

    admin = db.get(AdminUser, admin_id)
    if not admin or not admin.is_active:
        request.session.pop("admin_user_id", None)
        return None
    return admin


def _ensure_admin(request: Request, db: Session) -> Optional[AdminUser]:
    return _get_admin_from_session(request, db)


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-")


def _parse_image_entries(raw_entries: str) -> list[tuple[str, Optional[str]]]:
    entries: list[tuple[str, Optional[str]]] = []
    for line in raw_entries.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            url, alt = line.split("|", 1)
            entries.append((url.strip(), alt.strip() or None))
        else:
            entries.append((line, None))
    return entries


@router.get("", include_in_schema=False)
def admin_root(request: Request, db: Session = Depends(get_db)):
    if _get_admin_from_session(request, db):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
def admin_routing(request: Request, db: Session = Depends(get_db)):
    if _get_admin_from_session(request, db):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


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
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "page": "dashboard", "admin": admin},
    )


@router.get("/products", response_class=HTMLResponse)
def manage_products(request: Request, db: Session = Depends(get_db)):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    products_query = (
        select(
            Product.id,
            Product.name,
            Product.sku,
            Product.oem_number,
            Product.is_active,
            Category.name.label("category_name"),
        )
        .outerjoin(Category, Product.category_id == Category.id)
        .order_by(Product.created_at.desc())
    )
    rows = db.execute(products_query).all()
    products = [
        {
            "id": row.id,
            "name": row.name,
            "sku": row.sku,
            "oem_number": row.oem_number,
            "is_active": row.is_active,
            "category": row.category_name,
        }
        for row in rows
    ]

    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "page": "products",
            "admin": admin,
            "products": products,
        },
    )


@router.get("/products/new", response_class=HTMLResponse)
def new_product(request: Request, db: Session = Depends(get_db)):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    categories_raw = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
    category_options = [
        {"id": category.id, "name": category.name, "id_str": str(category.id)}
        for category in categories_raw
    ]

    context = {
        "request": request,
        "page": "products",
        "admin": admin,
        "form_error": None,
        "form_data": {
            "name": "",
            "sku": "",
            "oem_number": "",
            "summary": "",
            "category_id": "",
            "image_entries": "",
        },
        "categories": category_options,
    }
    return templates.TemplateResponse("admin/product_form.html", context)


@router.post("/products/new", response_class=HTMLResponse)
def create_product(
    request: Request,
    name: str = Form(...),
    sku: str = Form(...),
    oem_number: str = Form(...),
    summary: str = Form(""),
    category_id: str = Form(""),
    image_entries: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    name = name.strip()
    sku = sku.strip()
    oem_number = oem_number.strip()
    summary = summary.strip()
    category_value = category_id.strip() or None
    image_entries_value = image_entries.strip()

    categories_raw = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
    category_options = [
        {"id": category.id, "name": category.name, "id_str": str(category.id)}
        for category in categories_raw
    ]
    form_data = {
        "name": name,
        "sku": sku,
        "oem_number": oem_number,
        "summary": summary,
        "category_id": category_value or "",
        "image_entries": image_entries_value,
    }

    if not name or not sku or not oem_number:
        context = {
            "request": request,
            "page": "products",
            "admin": admin,
            "form_error": "Name, SKU, and OEM number are required.",
            "form_data": form_data,
            "categories": category_options,
        }
        return templates.TemplateResponse("admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    existing = db.scalars(
        select(Product).where(or_(Product.sku == sku, Product.oem_number == oem_number))
    ).first()
    if existing:
        context = {
            "request": request,
            "page": "products",
            "admin": admin,
            "form_error": "A product with this SKU or OEM number already exists.",
            "form_data": form_data,
            "categories": category_options,
        }
        return templates.TemplateResponse("admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    category_obj = None
    if category_value:
        try:
            category_pk = int(category_value)
        except ValueError:
            context = {
                "request": request,
                "page": "products",
                "admin": admin,
                "form_error": "Invalid category selection.",
                "form_data": form_data,
                "categories": category_options,
            }
            return templates.TemplateResponse(
                "admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST
            )

        category_obj = db.get(Category, category_pk)
        if not category_obj:
            context = {
                "request": request,
                "page": "products",
                "admin": admin,
                "form_error": "Selected category does not exist.",
                "form_data": form_data,
                "categories": category_options,
            }
            return templates.TemplateResponse(
                "admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST
            )

    image_pairs = _parse_image_entries(image_entries_value)

    product = Product(
        name=name,
        sku=sku,
        oem_number=oem_number,
        summary=summary,
        is_active=True,
    )
    if category_obj:
        product.category = category_obj

    for sort_order, (url, alt) in enumerate(image_pairs):
        if not url:
            continue
        product.images.append(
            ProductImage(
                image_url=url,
                alt_text=alt or name,
                sort_order=sort_order,
            )
        )

    db.add(product)
    db.commit()

    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories", response_class=HTMLResponse)
def manage_categories(request: Request, db: Session = Depends(get_db)):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    categories_query = (
        select(
            Category.id,
            Category.name,
            Category.slug,
            Category.is_active,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name.asc())
    )
    rows = db.execute(categories_query).all()
    categories = [
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "is_active": row.is_active,
            "product_count": row.product_count,
        }
        for row in rows
    ]

    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "page": "categories",
            "admin": admin,
            "categories": categories,
        },
    )


@router.get("/categories/new", response_class=HTMLResponse)
def new_category(request: Request, db: Session = Depends(get_db)):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    context = {
        "request": request,
        "page": "categories",
        "admin": admin,
        "form_error": None,
        "form_data": {"name": "", "slug": "", "description": ""},
    }
    return templates.TemplateResponse("admin/category_form.html", context)


@router.post("/categories/new", response_class=HTMLResponse)
def create_category(
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    name = name.strip()
    provided_slug = slug.strip()
    description = description.strip()

    form_data = {"name": name, "slug": provided_slug, "description": description}

    if not name:
        context = {
            "request": request,
            "page": "categories",
            "admin": admin,
            "form_error": "Category name is required.",
            "form_data": form_data,
        }
        return templates.TemplateResponse("admin/category_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    final_slug = provided_slug or _slugify(name)
    if not final_slug:
        context = {
            "request": request,
            "page": "categories",
            "admin": admin,
            "form_error": "Unable to generate a valid slug. Please provide one manually.",
            "form_data": form_data,
        }
        return templates.TemplateResponse("admin/category_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    existing = db.scalars(select(Category).where(Category.slug == final_slug)).first()
    if existing:
        context = {
            "request": request,
            "page": "categories",
            "admin": admin,
            "form_error": "A category with this slug already exists.",
            "form_data": form_data,
        }
        return templates.TemplateResponse("admin/category_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    category = Category(name=name, slug=final_slug, description=description, is_active=True)
    db.add(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)
