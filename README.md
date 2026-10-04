# WhistleDrop — Speak Without Being Seen

**WhistleDrop** is a backend-only confidential, anonymous reporting system built with Python and FastAPI. It allows individuals to safely report misconduct, ethical breaches, or security issues inside an organization without registering an account, providing personal data, or leaving identifiable fingerprints.

Upon submission, the reporter receives a cryptographically generated, unguessable **case code** (`WD-XXXX-...`). They can use this code at any time to inspect the progress and public status updates of their report. Authorized moderators can securely review and triage reports through authenticated endpoints without ever knowing or having access to reporter identity data.

---

## 1. Project Overview & Purpose

Many individuals hesitate to report critical organizational issues due to fear of retaliation, lack of trust in identity safeguards, or complex login procedures. WhistleDrop eliminates these barriers through a zero-identity, privacy-first architectural model:
- **No accounts or sign-ups**: Anyone can submit a report immediately.
- **No identifying telemetry**: Client IP addresses, browser user-agents, and session identifiers are intentionally excluded from the database and application logs.
- **Cryptographic one-way indexing**: Case codes are never stored in plaintext. The database retains only salted HMAC-SHA256 digests, protecting report access even against raw database inspection.
- **Controlled moderation**: Moderators review cases, update statuses, and communicate progress updates without any mechanism to unmask reporters.

---

## 2. Key Features

- **Anonymous Report Submission**: Post reports with category, description, and optional evidence URL.
- **Cryptographic Case Code Generation**: 128-bit entropy case codes generated via Python's `secrets` module.
- **HMAC-SHA256 Hashed Storage**: Only the one-way hash of the case code is stored in the database.
- **Public Anonymous Case Tracking**: Reporters track progress solely using their secret case code.
- **Strict Information Segregation**: Public tracking responses strictly omit internal database IDs, hashes, and private metadata.
- **HTTP Basic Authentication for Moderators**: Secure credentials loaded from environment variables with constant-time string comparison (`secrets.compare_digest`).
- **Moderator Triage & Filtering**: Filter reports by category and status, with pagination (`limit` and `offset`).
- **Deterministic Workflow State Machine**: Enforces valid status transitions (`SUBMITTED` &rarr; `UNDER_REVIEW` &rarr; `RESOLVED` / `DISMISSED`) and guarantees terminal states cannot be tampered with.
- **Defensive Privacy Headers**: Automatic HTTP headers (`Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).
- **Zero Frontend Footprint**: Pure REST API with integrated interactive OpenAPI/Swagger UI.

---

## 3. Technology Stack

- **Language**: Python 3.10+ (tested on Python 3.13)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance ASGI API framework)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **ORM & Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with [SQLite](https://sqlite.org/) (zero external setup required)
- **Data Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Environment Management**: `python-dotenv`
- **Testing**: [pytest](https://docs.pytest.org/) and `httpx` (`fastapi.testclient.TestClient`)

---

## 4. Folder Structure

```text
WhistleDrop_final/
├── app/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Pydantic Settings & environment variables
│   ├── database.py           # SQLAlchemy engine, session maker, get_db dependency
│   ├── models.py             # ORM models (Report, StatusUpdate)
│   ├── schemas.py            # Pydantic models & workflow transition logic
│   ├── security.py           # Cryptographic case code generator & HMAC hashing
│   ├── auth.py               # HTTP Basic authentication dependency
│   ├── main.py               # FastAPI application entrypoint & middleware
│   └── routers/
│       ├── __init__.py
│       ├── reports.py        # Public anonymous submission and tracking routes
│       └── moderator.py      # Authenticated moderator triage routes
├── tests/
│   ├── __init__.py
│   └── test_api.py           # Comprehensive pytest automated test suite (21 tests)
├── .env.example              # Template environment configuration
├── .env                      # Local environment configuration (ignored by git)
├── .gitignore                # Git ignore rules for secrets, DBs, and virtualenvs
├── requirements.txt          # Python dependencies
└── README.md                 # System documentation
```

---

## 5. Prerequisites

- **Python**: Version 3.10 or higher (Python 3.11, 3.12, and 3.13 supported).
- **Git**: For cloning and version control.
- **cURL / Postman / Browser**: To test API endpoints.

---

## 6. Setup and Installation

### 1. Clone or Open the Repository
```bash
cd WhistleDrop_final
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 7. Environment Configuration (`.env`)

Copy `.env.example` to create your local `.env` file:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On Linux / macOS:**
```bash
cp .env.example .env
```

### Configuration Variables:

```env
# Moderator HTTP Basic Auth Credentials
MODERATOR_USERNAME=moderator
MODERATOR_PASSWORD=change-this-password

# Secret key used for HMAC-SHA256 case code hashing
SECRET_KEY=replace-with-a-long-random-secret

# Database connection string (SQLite file)
DATABASE_URL=sqlite:///./whistledrop.db
```

> **Security Note:** In production, choose a strong, unique `SECRET_KEY` and high-entropy moderator credentials. Never commit your `.env` file to version control.

---

## 8. Starting the FastAPI Server

Run the development server with Uvicorn:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database tables (`reports` and `status_updates`) are automatically created on startup inside `whistledrop.db`.

---

## 9. Interactive API Documentation

Once the server is running, explore and test the endpoints directly from your browser:

- **Swagger UI (Interactive)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Alternative Reference)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON Specification**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 10. API Endpoints Reference

### Public / Anonymous Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/` | None | API service information and documentation links |
| `GET` | `/health` | None | Health check endpoint |
| `POST` | `/api/reports` | None | Submit a new anonymous misconduct report |
| `GET` | `/api/reports/track/{case_code}` | None | Track report status using one-time case code |

#### 1. Submit Report — `POST /api/reports`
- **Authentication**: None
- **Request Body**:
```json
{
  "category": "Harassment",
  "description": "Observed inappropriate conduct during the quarterly review meeting.",
  "evidence_url": "https://example.com/evidence/document.pdf"
}
```
*Note: `evidence_url` is optional.*
- **Allowed Categories**: `"Security"`, `"Harassment"`, `"Corruption"`, `"Technical"`, `"Other"`.
- **Response (`201 Created`)**:
```json
{
  "message": "Report submitted successfully.",
  "case_code": "WD-7A4B-391C-88EF-0012-BC9D-441F-238A"
}
```

#### 2. Track Report — `GET /api/reports/track/{case_code}`
- **Authentication**: None
- **Path Parameter**: `case_code` (e.g., `WD-7A4B-391C-88EF-0012-BC9D-441F-238A`)
- **Response (`200 OK`)**:
```json
{
  "case_code": "WD-7A4B-391C-88EF-0012-BC9D-441F-238A",
  "category": "Harassment",
  "status": "UNDER_REVIEW",
  "created_at": "2026-10-03T05:30:00.000000Z",
  "status_updates": [
    {
      "status": "SUBMITTED",
      "message": "Report submitted and pending review.",
      "created_at": "2026-10-03T05:30:00.000000Z"
    },
    {
      "status": "UNDER_REVIEW",
      "message": "The compliance team has commenced review.",
      "created_at": "2026-10-03T05:35:00.000000Z"
    }
  ]
}
```
- **Error Response (`404 Not Found`)**:
```json
{
  "detail": "Report not found with the provided case code."
}
```

---

### Moderator Endpoints

All moderator endpoints require **HTTP Basic Authentication** (`MODERATOR_USERNAME` & `MODERATOR_PASSWORD`).

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/moderator/reports` | Basic Auth | List reports with category/status filters and pagination |
| `GET` | `/api/moderator/reports/{report_id}` | Basic Auth | View complete report details and audit history |
| `PATCH` | `/api/moderator/reports/{report_id}/status` | Basic Auth | Update status and append public progress update |

#### 1. List Reports — `GET /api/moderator/reports`
- **Query Parameters**:
  - `category` *(optional)*: Filter by `Security`, `Harassment`, `Corruption`, `Technical`, `Other`.
  - `status` *(optional)*: Filter by `SUBMITTED`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED`.
  - `limit` *(optional, default: 20, max: 100)*: Items per page.
  - `offset` *(optional, default: 0)*: Items to skip.
- **Response (`200 OK`)**:
```json
{
  "total": 1,
  "limit": 20,
  "offset": 0,
  "reports": [
    {
      "id": 1,
      "category": "Harassment",
      "description": "Observed inappropriate conduct during the quarterly review meeting.",
      "evidence_url": "https://example.com/evidence/document.pdf",
      "status": "UNDER_REVIEW",
      "created_at": "2026-10-03T05:30:00.000000Z",
      "updated_at": "2026-10-03T05:35:00.000000Z"
    }
  ]
}
```

#### 2. Get Single Report — `GET /api/moderator/reports/{report_id}`
- **Response (`200 OK`)**:
```json
{
  "id": 1,
  "category": "Harassment",
  "description": "Observed inappropriate conduct during the quarterly review meeting.",
  "evidence_url": "https://example.com/evidence/document.pdf",
  "status": "UNDER_REVIEW",
  "created_at": "2026-10-03T05:30:00.000000Z",
  "updated_at": "2026-10-03T05:35:00.000000Z",
  "status_history": [
    {
      "id": 1,
      "status": "SUBMITTED",
      "message": "Report submitted and pending review.",
      "created_at": "2026-10-03T05:30:00.000000Z"
    },
    {
      "id": 2,
      "status": "UNDER_REVIEW",
      "message": "The compliance team has commenced review.",
      "created_at": "2026-10-03T05:35:00.000000Z"
    }
  ]
}
```

#### 3. Update Report Status — `PATCH /api/moderator/reports/{report_id}/status`
- **Request Body**:
```json
{
  "status": "RESOLVED",
  "message": "The incident has been thoroughly investigated and appropriate remedial steps taken."
}
```
- **Response (`200 OK`)**: Returns updated report with appended history.
- **Error Response (`400 Bad Request`)**: Returned if invalid workflow transition or modifying terminal status.

---

## 11. Example cURL Commands

### 1. Anonymous Report Submission
```bash
curl -X POST "http://127.0.0.1:8000/api/reports" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "Security",
    "description": "Exposed API token discovered in shared public documentation.",
    "evidence_url": "https://example.com/findings/token.png"
  }'
```

### 2. Track Report
```bash
curl -X GET "http://127.0.0.1:8000/api/reports/track/WD-7A4B-391C-88EF-0012-BC9D-441F-238A"
```

### 3. Moderator: List Reports (with Filtering & Pagination)
```bash
curl -X GET "http://127.0.0.1:8000/api/moderator/reports?category=Security&status=SUBMITTED&limit=10&offset=0" \
  -u "moderator:whistle-safe-pass-2026"
```

### 4. Moderator: View Report Details
```bash
curl -X GET "http://127.0.0.1:8000/api/moderator/reports/1" \
  -u "moderator:whistle-safe-pass-2026"
```

### 5. Moderator: Update Report Status
```bash
curl -X PATCH "http://127.0.0.1:8000/api/moderator/reports/1/status" \
  -u "moderator:whistle-safe-pass-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "UNDER_REVIEW",
    "message": "Security operations team has revoked the credential and initiated an audit."
  }'
```

---

## 12. How Anonymity Is Maintained & Its Limitations

### Technical Privacy Safeguards
1. **Zero Identification Requirement**: No reporter accounts, registration, names, email addresses, phone numbers, or passwords.
2. **Zero Ingestion of Client Telemetry**: No storage of IP addresses, HTTP `User-Agent`, geolocation, or fingerprinting headers.
3. **Cryptographic Hashing**: The plaintext case code is shown once to the reporter. The database stores only an HMAC-SHA256 digest keyed with `SECRET_KEY`. Database theft does not expose unhashed case codes.
4. **Information Separation**: Public responses never include internal database primary keys (`id`), foreign keys (`report_id`), or hash strings.
5. **No-Store HTTP Caching**: Middleware attaches `Cache-Control: no-store` to prevent caching of status lookups on intermediate proxy caches.

### Real-World Anonymity Limitations
- **Upstream Network Infrastructure**: Reverse proxies (NGINX, Cloudflare, AWS ALB), ISP logs, and cloud firewalls may log client IP addresses unless specifically configured to strip or discard them.
- **External Evidence URLs**: If a reporter includes an `evidence_url` pointing to a personal cloud storage link (e.g., Google Drive, OneDrive) or a link containing tracking tokens, opening that link could expose their identity to the host. Reporters should be advised to sanitize external links or use privacy-focused file sharing.
- **Timing & Writing Style**: Distinctive linguistics or reporting events that only one person could have witnessed can reveal identity regardless of technological anonymity.
- **Local Browser History**: Anyone with physical access to the reporter's device or browser history could discover the tracking URL if not using Private/Incognito browsing.

---

## 13. Status Workflow & State Machine

Every report progresses through a defined state machine:

```text
       [SUBMITTED]
         /     \
        /       \
       v         v
[UNDER_REVIEW]  [DISMISSED] (Terminal)
    /      \
   v        v
[RESOLVED] [DISMISSED] (Terminal)
(Terminal)
```

### Transition Rules:
- **`SUBMITTED`** &rarr; Can move to **`UNDER_REVIEW`** or **`DISMISSED`**.
- **`UNDER_REVIEW`** &rarr; Can move to **`RESOLVED`**, **`DISMISSED`**, or add progress messages while remaining **`UNDER_REVIEW`**.
- **`RESOLVED`** &rarr; **Terminal state**. Cannot be changed. Attempted changes return `400 Bad Request`.
- **`DISMISSED`** &rarr; **Terminal state**. Cannot be changed. Attempted changes return `400 Bad Request`.
- Skipping `UNDER_REVIEW` directly to `RESOLVED` from `SUBMITTED` is rejected with `400 Bad Request`.

---

## 14. Assumptions & Design Decisions

1. **HMAC-SHA256 for Case Codes**: Simple hashing (like unsalted SHA256) is vulnerable to dictionary and rainbow table lookups if the code space is small. HMAC-SHA256 keyed with a server-side `SECRET_KEY` ensures high resistance against offline attacks even if database contents are read.
2. **Deterministic Lookup**: By normalizing (stripping whitespace and uppercase conversion) before HMAC computation, reporters can enter codes without worrying about case-sensitivity issues, while preserving O(1) indexed database lookups.
3. **Status History as Separate Records**: Rather than merely mutating a status field, a `status_updates` relation maintains a permanent, timestamped progression record that serves both as an audit log for moderators and a progress log for the reporter.
4. **HTTP Basic Auth for Local Simplicity**: As per project specifications, HTTP Basic Authentication is used for moderators via environment variables. For multi-tenant production deployments, an enterprise IdP (e.g. OAuth2/OIDC/SAML) with Role-Based Access Control (RBAC) is recommended.

---

## 15. Running Automated Tests

A comprehensive test suite covering all functional requirements, security boundaries, and input validation is implemented in `tests/test_api.py`.

Tests run against an **isolated in-memory SQLite database** using SQLAlchemy's `StaticPool`, guaranteeing that test runs never alter or pollute your development database (`whistledrop.db`).

### Execute Tests:

**Using Python module execution (Recommended across all operating systems):**
```bash
python -m pytest -v
```

### Test Coverage Highlights (21 Tests):
- `test_submit_report_success`: Submits anonymously without credentials.
- `test_submit_report_omitted_evidence_url`: Tests optionality of evidence URL.
- `test_submit_report_reject_empty_or_whitespace_description`: Enforces non-empty content.
- `test_submit_report_reject_missing_description`: Rejects missing payload properties.
- `test_submit_report_reject_invalid_category`: Rejects unlisted categories.
- `test_submit_report_reject_malformed_evidence_url`: Validates URL format and scheme.
- `test_submit_report_returns_unique_case_codes`: Confirms entropy across submissions.
- `test_track_report_with_valid_case_code`: Validates case tracking using code.
- `test_track_report_rejects_invalid_case_code`: Returns safe 404 for unknown codes.
- `test_track_report_does_not_expose_internal_ids_or_hashes`: Verifies zero ID/hash leakage.
- `test_moderator_routes_reject_unauthenticated`: Validates 401 on missing auth.
- `test_moderator_routes_reject_invalid_credentials`: Validates 401 on incorrect credentials.
- `test_moderator_routes_accept_valid_credentials`: Validates 200 on authorized access.
- `test_moderator_list_and_filter_reports`: Tests category/status filtering & pagination.
- `test_moderator_view_report_detail`: Tests single report view and audit trail.
- `test_moderator_view_nonexistent_report`: Tests 404 on invalid ID.
- `test_status_workflow_progression`: Tests full `SUBMITTED` &rarr; `UNDER_REVIEW` &rarr; `RESOLVED`.
- `test_reject_invalid_status_transition`: Tests rejection of illegal transitions (e.g. `SUBMITTED` &rarr; `RESOLVED`).
- `test_reject_modifying_terminal_resolved_status`: Enforces terminal finality of `RESOLVED`.
- `test_reject_modifying_terminal_dismissed_status`: Enforces terminal finality of `DISMISSED`.
- `test_api_root_and_health`: Validates general endpoints.

---

## 16. Production Security Considerations

When transitioning WhistleDrop to a production environment:

1. **Proxy Web Server Configuration**: Deploy behind NGINX, Traefik, or Caddy with access logging configured to either disable IP address retention or hash IP addresses with a daily rotating salt for GDPR/privacy compliance.
2. **Enforce HTTPS (TLS 1.3)**: Never serve WhistleDrop over unencrypted HTTP. All public communication must be encrypted in transit.
3. **Database Migration to PostgreSQL**: For enterprise load, replace SQLite with PostgreSQL (`DATABASE_URL=postgresql://user:pass@host/db`). The SQLAlchemy models are fully compatible.
4. **Secret Management**: Store `SECRET_KEY` and moderator credentials in a dedicated secrets manager (AWS Secrets Manager, GCP Secret Manager, Vault) rather than static files.
5. **Rate Limiting & Anti-Abuse**: Introduce IP-independent rate limiting (such as Proof-of-Work challenges or Redis-backed bucket limiters) on `POST /api/reports` to deter automated spam without logging reporter IPs.
6. **File Attachment Scanning**: If direct file uploads are added in the future, automatically strip EXIF/IPTC metadata (camera serials, GPS coordinates, author names) and scan with an antivirus engine before storage.
