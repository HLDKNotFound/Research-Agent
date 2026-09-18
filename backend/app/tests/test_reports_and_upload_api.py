import io
import uuid
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
async def test_file_upload_and_reports_api(mock_cache_service):
    cache_service._client = mock_cache_service._client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register & Login Lead Researcher (Owner)
        reg_resp = await ac.post(
            "/api/v1/auth/register",
            json={"email": "lead@quantum.org", "password": "SecurePassword123!", "name": "Lead Researcher"},
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Register & Login Outsider (Unauthorized User)
        reg_outsider = await ac.post(
            "/api/v1/auth/register",
            json={"email": "outsider@evil.com", "password": "SecurePassword123!", "name": "Outsider"},
        )
        assert reg_outsider.status_code == 201
        outsider_token = reg_outsider.json()["access_token"]
        outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

        # 3. Create Project
        proj_resp = await ac.post(
            "/api/v1/projects",
            json={"name": "End-to-End Quantum Project", "description": "Testing full research loop"},
            headers=headers,
        )
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # 4. Strict RBAC Check: Outsider cannot upload files to Project
        unauth_upload = await ac.post(
            f"/api/v1/projects/{project_id}/files/upload",
            files={"file": ("unauth.txt", io.BytesIO(b"malicious"), "text/plain")},
            headers=outsider_headers,
        )
        assert unauth_upload.status_code == 403, "Outsider should be denied file upload"

        # 5. Upload Valid CSV Document
        csv_file_content = b"qubits,noise_level,fidelity_gain\n16,0.01,2.8\n32,0.015,3.1\n64,0.02,3.4\n127,0.025,3.6\n"
        upload_resp = await ac.post(
            f"/api/v1/projects/{project_id}/files/upload",
            files={"file": ("quantum_telemetry.csv", io.BytesIO(csv_file_content), "text/csv")},
            headers=headers,
        )
        assert upload_resp.status_code == 201
        file_data = upload_resp.json()
        assert file_data["filename"] == "quantum_telemetry.csv"
        assert file_data["status"] == "ready"
        assert file_data["size_bytes"] == len(csv_file_content)

        # 6. Upload Plain Text Document
        txt_content = b"Zero-noise extrapolation benchmark results on IBM Eagle 127-qubit processor."
        upload_txt_resp = await ac.post(
            f"/api/v1/projects/{project_id}/files/upload",
            files={"file": ("notes.txt", io.BytesIO(txt_content), "text/plain")},
            headers=headers,
        )
        assert upload_txt_resp.status_code == 201

        # 7. List Files & Validate Counts
        files_list_resp = await ac.get(f"/api/v1/projects/{project_id}/files", headers=headers)
        assert files_list_resp.status_code == 200
        assert files_list_resp.json()["total"] == 2

        # 8. Trigger Analysis Run (with execute_now=True to run full LangGraph pipeline)
        run_resp = await ac.post(
            f"/api/v1/projects/{project_id}/runs?execute_now=true",
            json={
                "project_id": project_id,
                "prompt": "Evaluate quantum fidelity gains from uploaded telemetry across qubits",
                "idempotency_key": "run-e2e-001",
            },
            headers=headers,
        )
        assert run_resp.status_code == 201, run_resp.text
        run_data = run_resp.json()
        assert run_data["status"] == "completed"
        assert run_data["progress_pct"] == 100
        assert run_data["idempotency_key"] == "run-e2e-001"
        run_id = run_data["id"]

        # 9. Test Idempotency: Duplicate run with same key returns identical Run
        idempotent_resp = await ac.post(
            f"/api/v1/projects/{project_id}/runs?execute_now=false",
            json={
                "project_id": project_id,
                "prompt": "Evaluate quantum fidelity gains from uploaded telemetry across qubits",
                "idempotency_key": "run-e2e-001",
            },
            headers=headers,
        )
        assert idempotent_resp.status_code == 201
        assert idempotent_resp.json()["id"] == run_id

        # Conflict on same idempotency_key with different prompt
        conflict_resp = await ac.post(
            f"/api/v1/projects/{project_id}/runs?execute_now=false",
            json={
                "project_id": project_id,
                "prompt": "Completely different prompt with colliding key",
                "idempotency_key": "run-e2e-001",
            },
            headers=headers,
        )
        assert conflict_resp.status_code == 409

        # 10. List Generated Reports
        reports_resp = await ac.get(f"/api/v1/projects/{project_id}/reports", headers=headers)
        assert reports_resp.status_code == 200
        reports_items = reports_resp.json()["items"]
        assert len(reports_items) >= 1
        report_id = reports_items[0]["id"]

        # Outsider cannot list reports
        unauth_reports = await ac.get(f"/api/v1/projects/{project_id}/reports", headers=outsider_headers)
        assert unauth_reports.status_code == 403

        # 11. Get Report Details (including modular sections & citations)
        report_detail_resp = await ac.get(f"/api/v1/reports/{report_id}", headers=headers)
        assert report_detail_resp.status_code == 200
        detail_data = report_detail_resp.json()
        assert len(detail_data["sections"]) in (3, 4)
        total_citations = sum(len(s.get("citations") or []) for s in detail_data["sections"])
        assert total_citations >= 1

        # Verify section titles
        section_titles = [s["title"] for s in detail_data["sections"]]
        assert any("Executive Summary" in t for t in section_titles)
        assert any("Empirical" in t for t in section_titles)

        # 12. Modular Section Editing (Targeted Update without re-running pipeline)
        target_section = detail_data["sections"][0]
        patch_sec_resp = await ac.patch(
            f"/api/v1/reports/{report_id}/sections/{target_section['id']}",
            json={"title": "1. Updated Executive Summary (Peer-Reviewed)", "content": "Revised executive findings."},
            headers=headers,
        )
        assert patch_sec_resp.status_code == 200
        updated_sec_data = patch_sec_resp.json()
        assert updated_sec_data["title"] == "1. Updated Executive Summary (Peer-Reviewed)"
        assert updated_sec_data["content"] == "Revised executive findings."

        # 13. Soft Delete Report
        del_resp = await ac.delete(f"/api/v1/reports/{report_id}", headers=headers)
        assert del_resp.status_code == 204

        # Listing reports should now return 0 items
        post_del_list = await ac.get(f"/api/v1/projects/{project_id}/reports", headers=headers)
        assert post_del_list.status_code == 200
        assert post_del_list.json()["total"] == 0

        # Direct access to soft-deleted report should return 404
        post_del_get = await ac.get(f"/api/v1/reports/{report_id}", headers=headers)
        assert post_del_get.status_code == 404
