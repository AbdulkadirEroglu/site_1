from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    slug = Column(String(160), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    level = Column(Integer, nullable=False, default=0)
    order = Column(Integer, nullable=False, default=0)
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    name = Column(String(160), nullable=False)
    sku = Column(String(120), nullable=False, unique=True)
    oem_number = Column(String(60), nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    category = relationship("Category", back_populates="products")


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
