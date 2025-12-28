import re

from markupsafe import Markup
import markdown as md
import bleach
from bleach.css_sanitizer import CSSSanitizer

_HTML_PATTERN = re.compile(r"</?[a-z][\s\S]*?>", re.IGNORECASE)

_ALLOWED_TAGS = [
    "a",
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "span",
    "ul",
    "ol",
    "li",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
]

_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "span": ["style"],
    "p": ["style"],
    "h1": ["style"],
    "h2": ["style"],
    "h3": ["style"],
    "h4": ["style"],
}

_ALLOWED_CSS = [
    "color",
    "background-color",
    "font-size",
    "font-family",
    "font-weight",
    "font-style",
    "text-decoration",
    "text-align",
    "line-height",
]

_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=_ALLOWED_CSS)


def render_rich_text(value: str) -> Markup:
    raw = (value or "").strip()
    if not raw:
        return Markup("")

    if _HTML_PATTERN.search(raw):
        html = raw
    else:
        html = md.markdown(raw, extensions=["extra", "sane_lists"])

    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
    )
    return Markup(cleaned)
