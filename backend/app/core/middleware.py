from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from app.core.config import settings

DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production-grade Security Headers Middleware adhering to modern OWASP guidelines.
    Includes:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 0 (replaces legacy vulnerable mode=block in favor of robust CSP)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Strict-Transport-Security (HSTS)
    - Context-Aware Content-Security-Policy (CSP): strict for API endpoints, relaxed for OpenAPI/Swagger documentation.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check HTTPS redirection if behind reverse proxy
        if settings.FORCE_HTTPS:
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
            if forwarded_proto != "https" and request.url.scheme != "https":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)

        response = await call_next(request)

        # Apply standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Apply HSTS if HTTPS is enabled or forwarded as HTTPS
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
            or settings.FORCE_HTTPS
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Context-Aware CSP:
        # For documentation endpoints (/docs, /redoc), allow swagger UI CDN assets and inline styles.
        path = request.url.path
        if any(path.startswith(doc_path) for doc_path in DOCS_PATHS):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com;"
            )
        else:
            # Strict API CSP
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        return response
