from passlib.context import CryptContext


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the provided password matches the stored hash."""
    if not plain_password or not hashed_password:
        return False
    return password_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash the provided password for storage."""
    return password_context.hash(password)
