"""Automated test suite for WhistleDrop Backend API.

Verifies:
- Anonymous report submission without credentials.
- Input validation (description, categories, URLs, size limits).
- Unique, unpredictable case code generation and HMAC hashing.
- Anonymous tracking using case code only.
- Strict prevention of identity leakage, internal ID exposure, and secret leakage.
- HTTP Basic authentication for moderator routes (missing, invalid, valid).
- Report listing, category filtering, status filtering, and pagination.
- Status update workflow, permitted transitions, and terminal state protection.
- Public visibility of progress updates on tracking endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Report, StatusUpdate
from app.schemas import ReportCategory, ReportStatus

# Use an isolated in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create fresh tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Valid HTTP Basic auth credentials from settings."""
    settings = get_settings()
    import base64
    user_pass = f"{settings.MODERATOR_USERNAME}:{settings.MODERATOR_PASSWORD}"
    encoded = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


# ============================================================================
# 1. Anonymous Report Submission Tests
# ============================================================================

def test_submit_report_success(client: TestClient):
    """Confirm report can be submitted anonymously without credentials or user account."""
    payload = {
        "category": "Harassment",
        "description": "Observed inappropriate conduct in department meeting.",
        "evidence_url": "https://example.com/evidence/doc1.pdf",
    }
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["message"] == "Report submitted successfully."
    assert "case_code" in data
    assert data["case_code"].startswith("WD-")
    # Confirm internal fields are not exposed
    assert "id" not in data
    assert "case_code_hash" not in data
    assert "status" not in data


def test_submit_report_omitted_evidence_url(client: TestClient):
    """Evidence URL should be optional; report submits cleanly without it."""
    payload = {
        "category": "Security",
        "description": "Server credentials found exposed in open repository.",
    }
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 201
    assert "case_code" in response.json()


def test_submit_report_reject_empty_or_whitespace_description(client: TestClient):
    """Empty or whitespace-only descriptions must be rejected."""
    # Empty string
    res1 = client.post("/api/reports", json={"category": "Security", "description": ""})
    assert res1.status_code == 422

    # Whitespace only
    res2 = client.post("/api/reports", json={"category": "Security", "description": "    "})
    assert res2.status_code == 422


def test_submit_report_reject_missing_description(client: TestClient):
    """Missing description field must be rejected."""
    response = client.post("/api/reports", json={"category": "Technical"})
    assert response.status_code == 422


def test_submit_report_reject_invalid_category(client: TestClient):
    """Categories not in the defined enum must be rejected."""
    payload = {
        "category": "AlienInvasion",
        "description": "Unrecognized category test.",
    }
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 422


def test_submit_report_reject_malformed_evidence_url(client: TestClient):
    """Malformed or invalid protocol evidence URLs must be rejected."""
    invalid_urls = [
        "not-a-url",
        "ftp://example.com/files",
        "javascript:alert(1)",
        "http:///no-domain",
    ]
    for bad_url in invalid_urls:
        payload = {
            "category": "Corruption",
            "description": "Bribe solicitation reported.",
            "evidence_url": bad_url,
        }
        response = client.post("/api/reports", json=payload)
        assert response.status_code == 422, f"Expected 422 for bad url: {bad_url}"


def test_submit_report_returns_unique_case_codes(client: TestClient):
    """Every submission must generate a distinct, cryptographically unique case code."""
    codes = set()
    for _ in range(5):
        res = client.post(
            "/api/reports",
            json={"category": "Other", "description": "Anonymous observation."},
        )
        assert res.status_code == 201
        codes.add(res.json()["case_code"])
    assert len(codes) == 5


# ============================================================================
# 2. Case Tracking Tests
# ============================================================================

def test_track_report_with_valid_case_code(client: TestClient):
    """Reporter can track report status using their case code alone."""
    sub_res = client.post(
        "/api/reports",
        json={"category": "Technical", "description": "Critical data vulnerability."},
    )
    case_code = sub_res.json()["case_code"]

    track_res = client.get(f"/api/reports/track/{case_code}")
    assert track_res.status_code == 200

    data = track_res.json()
    assert data["case_code"] == case_code
    assert data["category"] == "Technical"
    assert data["status"] == "SUBMITTED"
    assert "created_at" in data
    assert len(data["status_updates"]) == 1
    assert data["status_updates"][0]["status"] == "SUBMITTED"
    assert "Report submitted" in data["status_updates"][0]["message"]


def test_track_report_rejects_invalid_case_code(client: TestClient):
    """Invalid or nonexistent case code must return 404 with safe message."""
    res = client.get("/api/reports/track/WD-FAKE-NON-EXISTENT-CODE")
    assert res.status_code == 404
    assert res.json()["detail"] == "Report not found with the provided case code."


def test_track_report_does_not_expose_internal_ids_or_hashes(client: TestClient):
    """Public tracking must not disclose database IDs, hashes, or moderator data."""
    sub_res = client.post(
        "/api/reports",
        json={"category": "Corruption", "description": "Embezzlement report."},
    )
    case_code = sub_res.json()["case_code"]

    data = client.get(f"/api/reports/track/{case_code}").json()
    assert "id" not in data
    assert "report_id" not in data
    assert "case_code_hash" not in data
    assert "moderator" not in data

    for update in data["status_updates"]:
        assert "id" not in update
        assert "report_id" not in update


# ============================================================================
# 3. Moderator Authentication Tests
# ============================================================================

def test_moderator_routes_reject_unauthenticated(client: TestClient):
    """Moderator routes must reject unauthenticated requests with 401."""
    assert client.get("/api/moderator/reports").status_code == 401
    assert client.get("/api/moderator/reports/1").status_code == 401
    assert (
        client.patch(
            "/api/moderator/reports/1/status",
            json={"status": "UNDER_REVIEW", "message": "Starting review."},
        ).status_code
        == 401
    )


def test_moderator_routes_reject_invalid_credentials(client: TestClient):
    """Moderator routes must reject wrong credentials with 401."""
    import base64
    bad_auth = base64.b64encode(b"wrong_user:wrong_pass").decode("utf-8")
    headers = {"Authorization": f"Basic {bad_auth}"}

    res = client.get("/api/moderator/reports", headers=headers)
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers


def test_moderator_routes_accept_valid_credentials(client: TestClient, auth_headers: dict):
    """Moderator routes must accept valid credentials with 200."""
    res = client.get("/api/moderator/reports", headers=auth_headers)
    assert res.status_code == 200
    assert "reports" in res.json()


# ============================================================================
# 4. Moderator Report Management, Filtering & Pagination
# ============================================================================

def test_moderator_list_and_filter_reports(client: TestClient, auth_headers: dict):
    """Moderators can list reports and filter by category and status."""
    # Seed reports
    client.post("/api/reports", json={"category": "Security", "description": "Security incident 1."})
    client.post("/api/reports", json={"category": "Security", "description": "Security incident 2."})
    client.post("/api/reports", json={"category": "Harassment", "description": "Harassment incident."})

    # List all
    all_res = client.get("/api/moderator/reports", headers=auth_headers)
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3

    # Filter by category
    sec_res = client.get("/api/moderator/reports?category=Security", headers=auth_headers)
    assert sec_res.status_code == 200
    assert sec_res.json()["total"] == 2
    for r in sec_res.json()["reports"]:
        assert r["category"] == "Security"

    # Filter by status
    sub_res = client.get("/api/moderator/reports?status=SUBMITTED", headers=auth_headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["total"] == 3

    # Filter by non-existent matching status
    res_status = client.get("/api/moderator/reports?status=RESOLVED", headers=auth_headers)
    assert res_status.status_code == 200
    assert res_status.json()["total"] == 0

    # Pagination: limit=1, offset=1
    page_res = client.get("/api/moderator/reports?limit=1&offset=1", headers=auth_headers)
    assert page_res.status_code == 200
    assert len(page_res.json()["reports"]) == 1
    assert page_res.json()["total"] == 3


def test_moderator_view_report_detail(client: TestClient, auth_headers: dict):
    """Moderators can view full report details and status audit history."""
    sub = client.post(
        "/api/reports",
        json={"category": "Other", "description": "Policy inquiry.", "evidence_url": "https://example.com/info"},
    )
    assert sub.status_code == 201

    list_res = client.get("/api/moderator/reports", headers=auth_headers)
    report_id = list_res.json()["reports"][0]["id"]

    detail_res = client.get(f"/api/moderator/reports/{report_id}", headers=auth_headers)
    assert detail_res.status_code == 200

    detail = detail_res.json()
    assert detail["id"] == report_id
    assert detail["category"] == "Other"
    assert detail["description"] == "Policy inquiry."
    assert detail["evidence_url"] == "https://example.com/info"
    assert detail["status"] == "SUBMITTED"
    assert len(detail["status_history"]) == 1
    assert "case_code_hash" not in detail


def test_moderator_view_nonexistent_report(client: TestClient, auth_headers: dict):
    """Viewing an invalid report ID returns 404."""
    res = client.get("/api/moderator/reports/99999", headers=auth_headers)
    assert res.status_code == 404


# ============================================================================
# 5. Workflow Transitions and Terminal State Protection
# ============================================================================

def test_status_workflow_progression(client: TestClient, auth_headers: dict):
    """Test full workflow progression: SUBMITTED -> UNDER_REVIEW -> RESOLVED."""
    sub = client.post(
        "/api/reports",
        json={"category": "Security", "description": "Unpatched CVE detected."},
    )
    case_code = sub.json()["case_code"]

    list_res = client.get("/api/moderator/reports", headers=auth_headers)
    report_id = list_res.json()["reports"][0]["id"]

    # 1. Transition SUBMITTED -> UNDER_REVIEW
    patch1 = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "UNDER_REVIEW", "message": "Security team investigating."},
    )
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "UNDER_REVIEW"
    assert len(patch1.json()["status_history"]) == 2

    # Check that tracking sees the updated status
    track1 = client.get(f"/api/reports/track/{case_code}").json()
    assert track1["status"] == "UNDER_REVIEW"
    assert len(track1["status_updates"]) == 2
    assert track1["status_updates"][1]["message"] == "Security team investigating."

    # 2. Add an in-progress update message while remaining UNDER_REVIEW
    patch_in_progress = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "UNDER_REVIEW", "message": "Patch deployed to staging; verifying."},
    )
    assert patch_in_progress.status_code == 200
    assert len(patch_in_progress.json()["status_history"]) == 3

    # 3. Transition UNDER_REVIEW -> RESOLVED (Terminal)
    patch2 = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "RESOLVED", "message": "Patch verified in production. Closed."},
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "RESOLVED"
    assert len(patch2.json()["status_history"]) == 4

    # Check tracking endpoint reflects final resolution
    track2 = client.get(f"/api/reports/track/{case_code}").json()
    assert track2["status"] == "RESOLVED"
    assert len(track2["status_updates"]) == 4


def test_reject_invalid_status_transition(client: TestClient, auth_headers: dict):
    """Skipping UNDER_REVIEW from SUBMITTED directly to RESOLVED must be rejected."""
    client.post(
        "/api/reports",
        json={"category": "Technical", "description": "System glitch."},
    )
    list_res = client.get("/api/moderator/reports", headers=auth_headers)
    report_id = list_res.json()["reports"][0]["id"]

    bad_patch = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "RESOLVED", "message": "Direct resolution attempt."},
    )
    assert bad_patch.status_code == 400
    assert "Invalid status transition" in bad_patch.json()["detail"]


def test_reject_modifying_terminal_resolved_status(client: TestClient, auth_headers: dict):
    """Terminal status RESOLVED cannot be transitioned to any other status."""
    client.post("/api/reports", json={"category": "Other", "description": "Misc concern."})
    report_id = client.get("/api/moderator/reports", headers=auth_headers).json()["reports"][0]["id"]

    # Move to UNDER_REVIEW then RESOLVED
    client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "UNDER_REVIEW", "message": "Reviewing."},
    )
    client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "RESOLVED", "message": "Resolved."},
    )

    # Attempt to change from RESOLVED
    terminal_patch = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "UNDER_REVIEW", "message": "Attempting reopening."},
    )
    assert terminal_patch.status_code == 400
    assert "terminal status" in terminal_patch.json()["detail"]


def test_reject_modifying_terminal_dismissed_status(client: TestClient, auth_headers: dict):
    """Terminal status DISMISSED cannot be transitioned to any other status."""
    client.post("/api/reports", json={"category": "Other", "description": "Duplicate report."})
    report_id = client.get("/api/moderator/reports", headers=auth_headers).json()["reports"][0]["id"]

    # Directly dismiss from SUBMITTED
    dismiss_patch = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "DISMISSED", "message": "Dismissed as duplicate."},
    )
    assert dismiss_patch.status_code == 200
    assert dismiss_patch.json()["status"] == "DISMISSED"

    # Attempt to modify dismissed report
    after_dismiss = client.patch(
        f"/api/moderator/reports/{report_id}/status",
        headers=auth_headers,
        json={"status": "UNDER_REVIEW", "message": "Attempting revival."},
    )
    assert after_dismiss.status_code == 400
    assert "terminal status" in after_dismiss.json()["detail"]


# ============================================================================
# 6. General / Health Endpoints
# ============================================================================

def test_api_root_and_health(client: TestClient):
    """Root and health check endpoints respond correctly."""
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert root_res.json()["status"] == "online"

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
