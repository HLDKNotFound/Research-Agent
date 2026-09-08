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
async def test_conversations_and_runs_api(mock_cache_service):
    cache_service._client = mock_cache_service._client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register & login Primary User
        reg_resp = await ac.post(
            "/api/v1/auth/register",
            json={
                "email": "chatuser@nexus.org",
                "password": "Password123!",
                "name": "Chat User",
            },
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Register Unauthorized User
        reg_unauth = await ac.post(
            "/api/v1/auth/register",
            json={
                "email": "unauth@nexus.org",
                "password": "Password123!",
                "name": "Unauth User",
            },
        )
        assert reg_unauth.status_code == 201
        unauth_token = reg_unauth.json()["access_token"]
        unauth_headers = {"Authorization": f"Bearer {unauth_token}"}

        # 2. Create Project
        proj_resp = await ac.post(
            "/api/v1/projects",
            json={"name": "Quantum AI Project", "description": "Research on NISQ"},
            headers=headers,
        )
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # 3. Unauthorized user cannot create conversation in Project
        unauth_conv = await ac.post(
            f"/api/v1/projects/{project_id}/conversations",
            json={"project_id": project_id, "title": "Unauthorized Conversation"},
            headers=unauth_headers,
        )
        assert unauth_conv.status_code == 403

        # 4. Create Conversation
        conv_resp = await ac.post(
            f"/api/v1/projects/{project_id}/conversations",
            json={"project_id": project_id, "title": "Quantum Error Mitigation Chat"},
            headers=headers,
        )
        assert conv_resp.status_code == 201
        conv_data = conv_resp.json()
        assert conv_data["title"] == "Quantum Error Mitigation Chat"
        conversation_id = conv_data["id"]

        # 5. List Conversations
        list_resp = await ac.get(f"/api/v1/projects/{project_id}/conversations", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()["items"]) == 1

        # 6. Post Multiple Messages and Verify Strict Chronological Ordering
        m1 = await ac.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "conversation_id": conversation_id,
                "role": "user",
                "content": "What are zero-noise extrapolation techniques?",
            },
            headers=headers,
        )
        assert m1.status_code == 201

        m2 = await ac.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": "Zero-noise extrapolation (ZNE) fits polynomial error models to noisy measurements.",
            },
            headers=headers,
        )
        assert m2.status_code == 201

        # Unauthorized user cannot post to conversation
        m_unauth = await ac.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "conversation_id": conversation_id,
                "role": "user",
                "content": "Spam message",
            },
            headers=unauth_headers,
        )
        assert m_unauth.status_code == 403

        # 7. List Messages: strict count and chronological order
        msgs_resp = await ac.get(f"/api/v1/conversations/{conversation_id}/messages", headers=headers)
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[0]["created_at"] <= msgs[1]["created_at"]

        # 8. Create Analysis Run
        run_resp = await ac.post(
            f"/api/v1/projects/{project_id}/runs",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id,
                "prompt": "Investigate zero-noise extrapolation with 3 sources",
                "idempotency_key": "run-idemp-001",
            },
            headers=headers,
        )
        assert run_resp.status_code == 201
        run_id = run_resp.json()["id"]

        # 9. Stream Run Progress via SSE
        stream_resp = await ac.get(f"/api/v1/runs/{run_id}/stream", headers=headers)
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        body_text = stream_resp.text
        assert "Planner" in body_text
        assert "Critic / Verifier" in body_text

        # Unauthorized user cannot stream the run
        unauth_stream = await ac.get(f"/api/v1/runs/{run_id}/stream", headers=unauth_headers)
        assert unauth_stream.status_code == 403
