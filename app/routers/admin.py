import re
from collections import defaultdict
from typing import Any, Callable, Optional

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


def _category_parent_options(
    db: Session,
    *,
    include_predicate: Optional[Callable[[Category], bool]] = None,
) -> list[dict[str, str]]:
    categories = db.scalars(select(Category).order_by(Category.order.asc(), Category.name.asc())).all()
    children_map: dict[Optional[int], list[Category]] = defaultdict(list)
    for category in categories:
        children_map[category.parent_id].append(category)

    for siblings in children_map.values():
        siblings.sort(key=lambda c: (c.order, c.name.lower()))

    options: list[dict[str, str]] = []
    visited: set[int] = set()

    def _visit(node: Category, depth: int) -> None:
        prefix = "-- " * depth
        if not include_predicate or include_predicate(node):
            label = f"{prefix}{node.name}" if prefix else node.name
            options.append({"id": node.id, "id_str": str(node.id), "label": label})
        visited.add(node.id)
        for child in children_map.get(node.id, []):
            _visit(child, depth + 1)

    for root in children_map.get(None, []):
        _visit(root, 0)

    for category in categories:
        if category.id not in visited:
            _visit(category, 0)

    return options


def _category_tree_with_stats(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            Category.slug,
            Category.is_active,
            Category.parent_id,
            Category.order,
            Category.level,
            func.count(Product.id).label("product_count"),
        )
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(
            Category.id,
            Category.name,
            Category.slug,
            Category.is_active,
            Category.parent_id,
            Category.order,
            Category.level,
        )
    ).all()

    nodes: dict[int, dict[str, Any]] = {}
    children_map: dict[Optional[int], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        node = {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "is_active": row.is_active,
            "parent_id": row.parent_id,
            "order": row.order,
            "level": row.level,
            "product_count": row.product_count,
        }
        nodes[row.id] = node
        children_map[row.parent_id].append(node)

    for siblings in children_map.values():
        siblings.sort(key=lambda item: (item["order"], item["name"].lower()))

    ordered: list[dict[str, Any]] = []
    visited: set[int] = set()

    def _visit(node: dict[str, Any], depth: int) -> None:
        node["depth"] = depth
        ordered.append(node)
        visited.add(node["id"])
        for child in children_map.get(node["id"], []):
            _visit(child, depth + 1)

    for root in children_map.get(None, []):
        _visit(root, 0)

    for node in nodes.values():
        if node["id"] not in visited:
            _visit(node, 0)

    return ordered


def _render_categories_page(
    request: Request,
    admin: AdminUser,
    db: Session,
    *,
    message: Optional[str] = None,
    message_kind: str = "info",
) -> HTMLResponse:
    categories = _category_tree_with_stats(db)
    context = {
        "request": request,
        "page": "categories",
        "admin": admin,
        "categories": categories,
        "page_message": message,
        "page_message_kind": message_kind,
    }
    return templates.TemplateResponse("admin/categories.html", context)


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

    category_options = _category_parent_options(db, include_predicate=lambda cat: cat.is_active)

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
        "form_mode": "create",
        "form_action": "/admin/products/new",
        "submit_label": "Create product",
        "form_title": "Add product",
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

    category_options = _category_parent_options(db, include_predicate=lambda cat: cat.is_active)
    form_data = {
        "name": name,
        "sku": sku,
        "oem_number": oem_number,
        "summary": summary,
        "category_id": category_value or "",
        "image_entries": image_entries_value,
    }

    def _render_error(message: str):
        context = {
            "request": request,
            "page": "products",
            "admin": admin,
            "form_error": message,
            "form_data": form_data,
            "categories": category_options,
            "form_mode": "create",
            "form_action": "/admin/products/new",
            "submit_label": "Create product",
            "form_title": "Add product",
        }
        return templates.TemplateResponse("admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    if not name or not sku or not oem_number:
        return _render_error("Name, SKU, and OEM number are required.")

    existing = db.scalars(
        select(Product).where(or_(Product.sku == sku, Product.oem_number == oem_number))
    ).first()
    if existing:
        return _render_error("A product with this SKU or OEM number already exists.")

    category_obj = None
    if category_value:
        try:
            category_pk = int(category_value)
        except ValueError:
            return _render_error("Invalid category selection.")

        category_obj = db.get(Category, category_pk)
        if not category_obj:
            return _render_error("Selected category does not exist.")

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


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

    category_options = _category_parent_options(
        db, include_predicate=lambda cat: cat.is_active or cat.id == (product.category_id or -1)
    )
    images_serialized = []
    for image in sorted(product.images, key=lambda img: img.sort_order):
        if image.alt_text:
            images_serialized.append(f"{image.image_url} | {image.alt_text}")
        else:
            images_serialized.append(image.image_url)

    form_data = {
        "name": product.name,
        "sku": product.sku,
        "oem_number": product.oem_number,
        "summary": product.summary or "",
        "category_id": str(product.category_id) if product.category_id else "",
        "image_entries": "\n".join(images_serialized),
    }

    context = {
        "request": request,
        "page": "products",
        "admin": admin,
        "form_error": None,
        "form_data": form_data,
        "categories": category_options,
        "form_mode": "edit",
        "form_action": f"/admin/products/{product_id}/edit",
        "submit_label": "Update product",
        "form_title": f"Edit {product.name}",
        "product_id": product_id,
    }
    return templates.TemplateResponse("admin/product_form.html", context)


@router.post("/products/{product_id}/edit", response_class=HTMLResponse)
def update_product(
    request: Request,
    product_id: int,
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

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)

    name = name.strip()
    sku = sku.strip()
    oem_number = oem_number.strip()
    summary = summary.strip()
    category_value = category_id.strip() or None
    image_entries_value = image_entries.strip()

    category_options = _category_parent_options(
        db, include_predicate=lambda cat: cat.is_active or cat.id == (product.category_id or -1)
    )
    form_data = {
        "name": name,
        "sku": sku,
        "oem_number": oem_number,
        "summary": summary,
        "category_id": category_value or "",
        "image_entries": image_entries_value,
    }

    def _render_error(message: str):
        context = {
            "request": request,
            "page": "products",
            "admin": admin,
            "form_error": message,
            "form_data": form_data,
            "categories": category_options,
            "form_mode": "edit",
            "form_action": f"/admin/products/{product_id}/edit",
            "submit_label": "Update product",
            "form_title": f"Edit {product.name}",
            "product_id": product_id,
        }
        return templates.TemplateResponse("admin/product_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    if not name or not sku or not oem_number:
        return _render_error("Name, SKU, and OEM number are required.")

    existing = db.scalars(
        select(Product).where(
            or_(Product.sku == sku, Product.oem_number == oem_number),
            Product.id != product.id,
        )
    ).first()
    if existing:
        return _render_error("A product with this SKU or OEM number already exists.")

    category_obj = None
    if category_value:
        try:
            category_pk = int(category_value)
        except ValueError:
            return _render_error("Invalid category selection.")

        category_obj = db.get(Category, category_pk)
        if not category_obj:
            return _render_error("Selected category does not exist.")

    image_pairs = _parse_image_entries(image_entries_value)

    product.name = name
    product.sku = sku
    product.oem_number = oem_number
    product.summary = summary
    product.category = category_obj
    product.images.clear()

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

    return _render_categories_page(request, admin, db)


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
        "form_data": {"name": "", "slug": "", "description": "", "level": 0, "order": "", "parent_id": ""},
        "parent_options": _category_parent_options(db),
        "form_mode": "create",
        "form_action": "/admin/categories/new",
        "submit_label": "Create category",
        "form_title": "Add category",
        "parent_display": None,
    }
    return templates.TemplateResponse("admin/category_form.html", context)


@router.post("/categories/new", response_class=HTMLResponse)
def create_category(
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    order: str = Form(""),
    parent_id: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    name = name.strip()
    provided_slug = slug.strip()
    description = description.strip()
    order_raw = order.strip()
    parent_raw = parent_id.strip()
    parent_options = _category_parent_options(db)

    form_data = {
        "name": name,
        "slug": provided_slug,
        "description": description,
        "order": order_raw,
        "parent_id": parent_raw,
        "level": "0",
    }

    def _render_error(message: str):
        context = {
            "request": request,
            "page": "categories",
            "admin": admin,
            "form_error": message,
            "form_data": form_data,
            "parent_options": parent_options,
            "form_mode": "create",
            "form_action": "/admin/categories/new",
            "submit_label": "Create category",
            "form_title": "Add category",
            "parent_display": None,
        }
        return templates.TemplateResponse("admin/category_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)


    if not name:
        return _render_error("Category name is required.")

    final_slug = provided_slug or _slugify(name)
    if not final_slug:
        return _render_error("Unable to generate a valid slug. Please provide one manually.")

    existing = db.scalars(select(Category).where(Category.slug == final_slug)).first()
    if existing:
        return _render_error("A category with this slug already exists.")

    parent_obj = None
    if parent_raw:
        try:
            parent_pk = int(parent_raw)
        except ValueError:
            return _render_error("Invalid parent category selection.")

        parent_obj = db.get(Category, parent_pk)
        if not parent_obj:
            return _render_error("Selected parent category does not exist.")

    effective_level = (parent_obj.level + 1) if parent_obj else 0
    form_data["level"] = str(effective_level)
    form_data["parent_id"] = str(parent_obj.id) if parent_obj else ""

    if order_raw:
        try:
            order_value = int(order_raw)
        except ValueError:
            return _render_error("Order must be an integer.")
        form_data["order"] = str(order_value)
    else:
        if parent_obj:
            sibling_filter = Category.parent_id == parent_obj.id
        else:
            sibling_filter = Category.parent_id.is_(None)
        max_order = db.execute(select(func.coalesce(func.max(Category.order), -1)).where(sibling_filter)).scalar_one()
        order_value = max_order + 1
        form_data["order"] = str(order_value)

    category = Category(
        name=name,
        slug=final_slug,
        description=description,
        is_active=True,
        order=order_value,
        level=effective_level,
        parent=parent_obj,
    )
    db.add(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
def edit_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    category = db.get(Category, category_id)
    if not category:
        return _render_categories_page(request, admin, db, message="Category not found.", message_kind="error")

    parent = category.parent
    parent_label = parent.name if parent else "No parent (top-level)"
    form_data = {
        "name": category.name,
        "slug": category.slug,
        "description": category.description or "",
        "order": str(category.order),
        "parent_id": str(parent.id) if parent else "",
        "level": str(category.level),
    }

    context = {
        "request": request,
        "page": "categories",
        "admin": admin,
        "form_error": None,
        "form_data": form_data,
        "parent_options": None,
        "form_mode": "edit",
        "form_action": f"/admin/categories/{category_id}/edit",
        "submit_label": "Update category",
        "form_title": f"Edit {category.name}",
        "parent_display": parent_label,
        "category_id": category_id,
    }
    return templates.TemplateResponse("admin/category_form.html", context)


@router.post("/categories/{category_id}/edit", response_class=HTMLResponse)
def update_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    order: str = Form(""),
    parent_id: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    category = db.get(Category, category_id)
    if not category:
        return _render_categories_page(request, admin, db, message="Category not found.", message_kind="error")

    name = name.strip()
    provided_slug = slug.strip()
    description = description.strip()
    order_raw = order.strip()

    parent = category.parent
    parent_label = parent.name if parent else "No parent (top-level)"

    form_data = {
        "name": name,
        "slug": provided_slug,
        "description": description,
        "order": order_raw or str(category.order),
        "parent_id": str(parent.id) if parent else "",
        "level": str(category.level),
    }

    def _render_error(message: str):
        context = {
            "request": request,
            "page": "categories",
            "admin": admin,
            "form_error": message,
            "form_data": form_data,
            "parent_options": None,
            "form_mode": "edit",
            "form_action": f"/admin/categories/{category_id}/edit",
            "submit_label": "Update category",
            "form_title": f"Edit {category.name}",
            "parent_display": parent_label,
            "category_id": category_id,
        }
        return templates.TemplateResponse("admin/category_form.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    if not name:
        return _render_error("Category name is required.")

    final_slug = provided_slug or _slugify(name)
    if not final_slug:
        return _render_error("Unable to generate a valid slug. Please provide one manually.")

    existing = db.scalars(
        select(Category).where(Category.slug == final_slug, Category.id != category.id)
    ).first()
    if existing:
        return _render_error("A category with this slug already exists.")

    if order_raw:
        try:
            order_value = int(order_raw)
        except ValueError:
            return _render_error("Order must be an integer.")
    else:
        order_value = category.order

    category.name = name
    category.slug = final_slug
    category.description = description
    category.order = order_value

    db.add(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/delete", response_class=HTMLResponse)
def delete_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    category = db.get(Category, category_id)
    if not category:
        return _render_categories_page(request, admin, db, message="Category not found.", message_kind="error")

    to_visit = [category]
    collected_ids: list[int] = []
    while to_visit:
        current = to_visit.pop()
        collected_ids.append(current.id)
        to_visit.extend(list(current.children))

    product_count = db.execute(
        select(func.count(Product.id)).where(Product.category_id.in_(collected_ids))
    ).scalar_one()
    if product_count > 0:
        return _render_categories_page(
            request,
            admin,
            db,
            message="Cannot delete a category that still has products assigned. Reassign products first.",
            message_kind="error",
        )

    db.delete(category)
    db.commit()

    return RedirectResponse(url="/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/products/{product_id}/delete", response_class=HTMLResponse)
def delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
):
    admin = _ensure_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    prod = db.get(Product, product_id)
    if not prod:
        return _render_categories_page(request, admin, db, message="Product not found.", message_kind="error")

    db.delete(prod)
    db.commit()

    return RedirectResponse(url="/admin/products", status_code=status.HTTP_303_SEE_OTHER)