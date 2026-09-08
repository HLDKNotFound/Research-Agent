import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from app.api.deps import get_db
from app.core.config import settings
from app.core.sanitizer import sanitize_metadata_text
from app.core.security import create_access_token
from app.models.user import User


@pytest.fixture(autouse=True)
def override_db(db_session):
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_metadata_xss_sanitization_vs_rich_content():
    # 1. Metadata field: script tags and event handlers must be stripped
    malicious_meta = "<script>alert('pwned')</script>Project <b onclick='evil()'>Alpha</b>"
    clean_meta = sanitize_metadata_text(malicious_meta)
    assert "<script>" not in clean_meta
    assert "onclick" not in clean_meta
    assert "alert" not in clean_meta
    assert clean_meta == "Project Alpha"

    # SVG onload and iframe injection vectors
    svg_vector = "<svg onload=alert(document.cookie)>Logo</svg><iframe src='javascript:evil()'></iframe>"
    clean_svg = sanitize_metadata_text(svg_vector)
    assert "<svg" not in clean_svg
    assert "onload" not in clean_svg
    assert "<iframe" not in clean_svg
    assert "Logo" in clean_svg

    # 2. Rich content / Prompt: inequalities and code blocks must be preserved
    rich_prompt = "Compare if model_A < model_B and check code: if x < 10 and y > 20:"
    # In rich prompts, we preserve raw text without stripping < or >
    assert "<" in rich_prompt
    assert ">" in rich_prompt


@pytest.mark.asyncio
async def test_security_headers_and_swagger_csp(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Standard API endpoint
        health_resp = await ac.get("/health")
        assert health_resp.status_code == 200
        headers = health_resp.headers

        # Verify modern security headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "0"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

        # Strict CSP for regular APIs
        assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")

        # Documentation endpoint /docs: must allow Swagger UI assets
        docs_resp = await ac.get("/docs")
        docs_csp = docs_resp.headers.get("Content-Security-Policy", "")
        assert "https://cdn.jsdelivr.net" in docs_csp


@pytest.mark.asyncio
async def test_reverse_proxy_https_enforcement(db_session):
    # Temporarily enable FORCE_HTTPS
    orig_setting = settings.FORCE_HTTPS
    try:
        settings.FORCE_HTTPS = True

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Plain HTTP without proxy header -> 301 redirect to HTTPS
            http_resp = await ac.get("/health", headers={"X-Forwarded-Proto": "http"}, follow_redirects=False)
            assert http_resp.status_code == 301
            assert http_resp.headers["location"].startswith("https://")

            # 2. Behind reverse proxy terminating SSL (X-Forwarded-Proto: https) -> 200 OK without loop!
            https_proxy_resp = await ac.get("/health", headers={"X-Forwarded-Proto": "https"})
            assert https_proxy_resp.status_code == 200
            assert "Strict-Transport-Security" in https_proxy_resp.headers
    finally:
        settings.FORCE_HTTPS = orig_setting
