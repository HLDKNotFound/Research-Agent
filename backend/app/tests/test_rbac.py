import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from app.api.deps import get_db
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
async def test_rbac_and_privilege_escalation(db_session):
    # Setup 4 users: Owner, Admin, Member, Viewer + 1 Superuser
    u_owner = User(email="owner@test.com", password_hash="hash", name="Owner")
    u_admin = User(email="admin@test.com", password_hash="hash", name="Admin")
    u_member = User(email="member@test.com", password_hash="hash", name="Member")
    u_viewer = User(email="viewer@test.com", password_hash="hash", name="Viewer")
    u_superuser = User(email="root@test.com", password_hash="hash", name="Super", is_superuser=True)

    db_session.add_all([u_owner, u_admin, u_member, u_viewer, u_superuser])
    await db_session.flush()

    token_owner = create_access_token(u_owner.id)
    token_admin = create_access_token(u_admin.id)
    token_member = create_access_token(u_member.id)
    token_viewer = create_access_token(u_viewer.id)
    token_superuser = create_access_token(u_superuser.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Owner creates project
        create_resp = await ac.post(
            "/api/v1/projects",
            json={"name": "Quantum Research", "description": "Physics lab"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # 2. Owner adds Admin, Member, Viewer
        await ac.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": str(u_admin.id), "role": "admin"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        await ac.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": str(u_member.id), "role": "member"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        await ac.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": str(u_viewer.id), "role": "viewer"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )

        # 3. Viewer permissions check
        # Viewer can read
        v_read = await ac.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {token_viewer}"})
        assert v_read.status_code == 200
        # Viewer blocked from mutating (PATCH)
        v_patch = await ac.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Hacked by Viewer"},
            headers={"Authorization": f"Bearer {token_viewer}"},
        )
        assert v_patch.status_code == 403

        # 4. Member permissions check
        # Member blocked from updating project settings
        m_patch = await ac.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Hacked by Member"},
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert m_patch.status_code == 403

        # 5. Admin can update project
        a_patch = await ac.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Quantum Research (Renamed by Admin)"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert a_patch.status_code == 200

        # 6. Admin-on-Admin Privilege Escalation Guard
        # Admin CANNOT invite someone as admin or owner
        dummy_user_id = str(uuid.uuid4())
        a_escalate = await ac.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": dummy_user_id, "role": "admin"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert a_escalate.status_code == 403
        assert "Admins can only assign 'member' or 'viewer'" in a_escalate.json()["detail"]

        # Admin CANNOT remove Owner
        a_remove_owner = await ac.delete(
            f"/api/v1/projects/{project_id}/members/{u_owner.id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert a_remove_owner.status_code == 403

        # Admin CAN remove Member
        a_remove_member = await ac.delete(
            f"/api/v1/projects/{project_id}/members/{u_member.id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert a_remove_member.status_code == 204

        # 7. The Last Owner Problem
        # Owner cannot leave without transferring ownership
        o_leave = await ac.delete(
            f"/api/v1/projects/{project_id}/members/{u_owner.id}",
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        assert o_leave.status_code == 403
        assert "The project owner cannot be removed" in o_leave.json()["detail"]

        # 8. Transfer Ownership: Owner transfers ownership to Admin
        transfer_resp = await ac.post(
            f"/api/v1/projects/{project_id}/transfer-ownership",
            json={"new_owner_user_id": str(u_admin.id)},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        assert transfer_resp.status_code == 204

        # Now u_admin is owner, so u_admin can delete the project
        del_resp = await ac.delete(
            f"/api/v1/projects/{project_id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert del_resp.status_code == 204

        # 9. Superuser bypass and Non-member rejection
        # Create another project by owner
        p2_resp = await ac.post(
            "/api/v1/projects",
            json={"name": "Secret Lab"},
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        p2_id = p2_resp.json()["id"]

        # Non-members must be rejected with 404 to avoid tenant ID enumeration
        unauth_p2_viewer = await ac.get(
            f"/api/v1/projects/{p2_id}",
            headers={"Authorization": f"Bearer {token_viewer}"},
        )
        assert unauth_p2_viewer.status_code == 404
        assert "not a member" in unauth_p2_viewer.json()["detail"]

        unauth_p2_del = await ac.delete(
            f"/api/v1/projects/{p2_id}",
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert unauth_p2_del.status_code == 404

        # Superuser was never added to p2 members, but can access it via global superuser privilege
        root_resp = await ac.get(
            f"/api/v1/projects/{p2_id}",
            headers={"Authorization": f"Bearer {token_superuser}"},
        )
        assert root_resp.status_code == 200
        assert root_resp.json()["name"] == "Secret Lab"
