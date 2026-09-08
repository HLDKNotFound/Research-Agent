import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from app.api.deps import get_db
from app.core.cache import cache_service


@pytest.fixture(autouse=True)
def override_db(db_session):
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_full_flow_and_rtr(mock_cache_service):
    # Bind cache service to fakeredis
    cache_service._client = mock_cache_service._client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Password complexity / input validation: Short password must be rejected
        short_pw_resp = await ac.post(
            "/api/v1/auth/register",
            json={"email": "weak@research.org", "password": "123", "name": "Weak User"},
        )
        assert short_pw_resp.status_code == 422

        # 2. Register valid user
        reg_resp = await ac.post(
            "/api/v1/auth/register",
            json={
                "email": "sarah@research.org",
                "password": "strongPassword123!",
                "name": "Sarah Connor",
            },
        )
        assert reg_resp.status_code == 201
        data = reg_resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        access_token = data["access_token"]
        refresh_token_1 = data["refresh_token"]

        # 3. Duplicate registration rejected with 409
        dup_resp = await ac.post(
            "/api/v1/auth/register",
            json={
                "email": "sarah@research.org",
                "password": "strongPassword123!",
            },
        )
        assert dup_resp.status_code == 409

        # 4. SQL Injection in login endpoint must be safely rejected (401 or 422 input validation)
        sqli_resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "sqli@test.com' OR 1=1 --", "password": "' OR '1'='1"},
        )
        assert sqli_resp.status_code in (401, 422)

        # 5. Wrong password rejected
        wrong_pw_resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "sarah@research.org", "password": "WrongPassword999!"},
        )
        assert wrong_pw_resp.status_code == 401

        # 6. Valid login works
        login_resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "sarah@research.org", "password": "strongPassword123!"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

        # 7. Access protected /me endpoint with access token
        me_resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "sarah@research.org"

        # 8. Forged or completely malformed bearer tokens rejected
        forged_resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer forged.token.signature"},
        )
        assert forged_resp.status_code == 401

        # 9. Presenting refresh token to access-only route must be REJECTED (token type validation)
        invalid_type_resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token_1}"},
        )
        assert invalid_type_resp.status_code == 401
        assert "expected 'access', got 'refresh'" in invalid_type_resp.json()["detail"]

        # 10. Presenting access token to /refresh endpoint must be REJECTED (token type validation)
        invalid_refresh_resp = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert invalid_refresh_resp.status_code == 401
        assert "expected 'refresh', got 'access'" in invalid_refresh_resp.json()["detail"]

        # 11. Refresh Token Rotation (RTR): Valid refresh
        ref_resp = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
        )
        assert ref_resp.status_code == 200
        new_data = ref_resp.json()
        new_access_token = new_data["access_token"]
        refresh_token_2 = new_data["refresh_token"]
        assert refresh_token_2 != refresh_token_1

        # Verify new access token works
        me_resp_2 = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_resp_2.status_code == 200

        # 12. Replay Attack Detection: Presenting the already-used refresh_token_1 again!
        replay_resp = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
        )
        # Should detect reuse attack and revoke the whole family
        assert replay_resp.status_code == 401
        assert "reuse detected" in replay_resp.json()["detail"]

        # 13. Further requests with refresh_token_2 must now fail because family was revoked
        subsequent_resp = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_2},
        )
        assert subsequent_resp.status_code == 401
        assert "Compromised" in subsequent_resp.json()["detail"]
