import secrets

from fastapi import HTTPException, Request, status


CSRF_SESSION_KEY = "_csrf_token"


def ensure_csrf_token(request: Request) -> str:
    """Return the CSRF token for the session, creating one if needed."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(request: Request, provided_token: str) -> None:
    """Validate the provided token against the session."""
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not provided_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CSRF token.")

    if not secrets.compare_digest(expected, provided_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CSRF token.")
