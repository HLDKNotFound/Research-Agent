import html
import re
from typing import Optional, Set
from app.core.exceptions import DomainException

# HTML tag stripping regex (for metadata fields only)
HTML_TAG_RE = re.compile(r"<[^>]+>")
DANGEROUS_JS_RE = re.compile(r"(javascript:|data:text/html|vbscript:)", re.IGNORECASE)
DANGEROUS_EVENTS_RE = re.compile(r"on\w+\s*=", re.IGNORECASE)


def sanitize_metadata_text(text: Optional[str], max_length: int = 255) -> Optional[str]:
    """
    Sanitizes metadata fields (e.g. user names, project titles, file labels):
    - Strips dangerous HTML tags and event handlers.
    - Prevents script injection in plain text UI elements.
    - Truncates to max_length.
    NOTE: DO NOT use this for prompts, agent outputs, or markdown content,
    as it would corrupt mathematical inequalities (<, >) or code snippets.
    """
    if text is None:
        return None

    # Truncate to bound length first to avoid ReDoS
    trimmed = text[:max_length].strip()

    # Remove script tags and contents
    cleaned = re.sub(r"<script.*?>.*?</script>", "", trimmed, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    cleaned = HTML_TAG_RE.sub("", cleaned)
    # Remove event handlers (e.g. onerror=, onclick=)
    cleaned = DANGEROUS_EVENTS_RE.sub("", cleaned)
    # Remove javascript: protocols
    cleaned = DANGEROUS_JS_RE.sub("", cleaned)

    return cleaned.strip()


def validate_safe_identifier(identifier: str, allowed_identifiers: Set[str]) -> str:
    """
    Guards against SQL Injection in dynamic order_by or column filter parameters.
    Only allows exact matches against a strict whitelist set.
    """
    clean_id = identifier.lower().strip()
    if clean_id not in allowed_identifiers:
        raise DomainException(
            f"Invalid identifier '{identifier}'. Allowed values: {sorted(list(allowed_identifiers))}"
        )
    return clean_id


def sanitize_email(email: str) -> str:
    """Normalizes and cleans email strings."""
    return email.lower().strip()
