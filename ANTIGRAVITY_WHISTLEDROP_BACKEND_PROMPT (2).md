# Antigravity IDE Prompt --- WhistleDrop Backend

## Project: WhistleDrop --- Speak Without Being Seen

Build a **backend-only confidential reporting system** named
**WhistleDrop**.

### Important project constraints

-   Build **only the backend**.
-   Do **not** create a frontend, UI, UX, HTML pages, templates,
    React/Vue/Angular app, or dashboard interface.
-   The system must be usable through REST API requests using Swagger
    UI, Postman, or cURL.
-   Use **Python + FastAPI** for the API.
-   Use **SQLite + SQLAlchemy** for persistence so the project can run
    locally without a separate database server.
-   Keep the implementation beginner-friendly, cleanly structured, and
    easy to run in VS Code or another IDE.
-   Do not stop after generating a plan. Create the working project
    files, implement the endpoints, add tests, and write the README.

------------------------------------------------------------------------

## 1. Purpose

WhistleDrop allows anyone to report misconduct or other concerns inside
an organization without creating an account or revealing their identity.

A reporter receives a unique, hard-to-guess case code. They can later
use that code to check the report's status and public updates.
Moderators can securely access and manage reports, but must never be
given reporter identity information.

The application must protect anonymity throughout the reporting process
while allowing moderators to review and act on reports.

## 2. Technology and project structure

Use: - Python 3.10+ - FastAPI - Uvicorn - SQLAlchemy - SQLite - Pydantic
for request/response validation - `python-dotenv` or Pydantic settings
for environment variables - `pytest` and FastAPI's `TestClient` for
automated tests

Create a clear structure similar to:

``` text
whistledrop/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── security.py
│   └── routers/
│       ├── __init__.py
│       ├── reports.py
│       └── moderator.py
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

You may adjust the structure if there is a clear reason, but keep
related code separated and avoid unnecessary complexity.

## 3. Report submission --- anonymous

Provide an endpoint that allows a person to submit a report without
registering or logging in.

Each report must contain:

-   `category` --- required; one of:
    -   `Security`
    -   `Harassment`
    -   `Corruption`
    -   `Technical`
    -   `Other`
-   `description` --- required, non-empty text
-   `evidence_url` --- optional URL pointing to supporting evidence or a
    reference

Requirements: - Validate all incoming fields. - Reject missing
descriptions, invalid categories, malformed URLs, and excessively large
input. - Do not ask for a name, email address, phone number, username,
or account. - Do not collect reporter identity or create a reporter
account. - Do not store IP addresses, user-agent values, or other
identifying request metadata in the report database. - Do not include
sensitive request details in application logs. - Return a newly
generated case code after successful submission. - The case code must be
generated using Python's `secrets` module or another cryptographically
secure random generator. It must be sufficiently long and unpredictable;
do not use sequential IDs, timestamps, or simple random numbers. - Store
only a hash of the case code in the database if practical. The original
case code should be shown only in the submission response. If hashing
it, implement secure lookup by hashing the supplied code in the same
way. - Never return internal database IDs or the case-code hash to
public callers.

Suggested endpoint:

`POST /api/reports`

Example request:

``` json
{
  "category": "Harassment",
  "description": "I would like to report an incident that occurred at work.",
  "evidence_url": "https://example.com/reference"
}
```

Example response:

``` json
{
  "message": "Report submitted successfully.",
  "case_code": "WD-EXAMPLE-ONE-TIME-SECRET"
}
```

The example case code is illustrative only. Generate a fresh secure
value for every real report.

## 4. Case tracking --- reporter access

Provide a public endpoint that lets a reporter check their report using
only their case code.

Suggested endpoint:

`GET /api/reports/track/{case_code}`

The response should contain only information safe for the anonymous
reporter to see:

-   Case code (or a safe display representation)
-   Current status
-   Relevant status updates
-   Submission date, if useful and safe

Do not return: - Internal database IDs - Moderator usernames or
credentials - Private moderator notes - Case-code hashes - Reporter
identity information (none should be collected) - Other reports or
information belonging to other cases

A missing or invalid case code should return a suitable error, such as
`404 Not Found`, with a clear but non-revealing message.

## 5. Report status and workflow

Every report must have a status.

Allowed statuses and normal workflow:

`SUBMITTED → UNDER_REVIEW → RESOLVED`

or

`SUBMITTED → UNDER_REVIEW → DISMISSED`

Requirements: - A new report must start with `SUBMITTED`. - Moderators
can update a report's status. - Validate status values and reject
unsupported values. - Enforce sensible transitions. For example, a
report can move from `SUBMITTED` to `UNDER_REVIEW`, then to `RESOLVED`
or `DISMISSED`. - Treat `RESOLVED` and `DISMISSED` as terminal statuses
unless an explicitly documented administrative reopening feature is
implemented. - A moderator must be able to add a short status update
explaining the progress. - Store status updates with a timestamp. -
Public tracking must show appropriate status updates, but never show
private moderator notes. - Consider keeping a status-history record
rather than overwriting the previous status without a trace.

Suggested status update fields: - `status` - `message` - `created_at`

Suggested endpoint:

`PATCH /api/moderator/reports/{report_id}/status`

Example request:

``` json
{
  "status": "UNDER_REVIEW",
  "message": "The report has been received and is being reviewed."
}
```

Use a separate internal report identifier for moderator routes if
needed. Never expose that identifier through the public tracking
response.

## 6. Moderator authentication and access

Provide secure moderator-only endpoints.

For this local project, implement HTTP Basic authentication using
credentials configured through environment variables. Do not hardcode
real credentials in source code.

Environment variables:

``` env
MODERATOR_USERNAME=moderator
MODERATOR_PASSWORD=change-this-password
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///./whistledrop.db
```

Requirements: - Load credentials and secrets from `.env`; provide
`.env.example` with placeholder values only. - Add `.env` and database
files to `.gitignore`. - Compare credentials safely and use an
appropriate password-hashing approach where credentials are stored. - If
using a single moderator account from environment variables, clearly
document that this is a simple development setup and recommend a proper
user store/strong secret management for production. - Protect every
moderator route with authentication. - Return `401 Unauthorized` for
missing or invalid credentials. - Do not include credentials, secret
keys, or hashes in API responses or logs. - Moderators must not be able
to identify who submitted a report. Do not add reporter identity fields.

## 7. Moderator report management

Implement authenticated endpoints that allow moderators to:

-   View submitted reports.
-   View report details.
-   Filter reports by category.
-   Filter reports by status.
-   Combine category and status filters.
-   Update a report's status.
-   Add a short status update.
-   Optionally search report descriptions if implemented safely.

Suggested endpoints:

  ---------------------------------------------------------------------------------------------
  Method                  Endpoint                                      Purpose
  ----------------------- --------------------------------------------- -----------------------
  `GET`                   `/api/moderator/reports`                      List reports; support
                                                                        optional `category` and
                                                                        `status` query filters

  `GET`                   `/api/moderator/reports/{report_id}`          View one report

  `PATCH`                 `/api/moderator/reports/{report_id}/status`   Update status and add a
                                                                        status message
  ---------------------------------------------------------------------------------------------

Use pagination (`limit` and `offset`) for the report list. Validate
pagination values and set a reasonable maximum page size.

Moderator responses may include report category, description, evidence
URL, current status, timestamps, and status history. They must not
include reporter identity information or case-code hashes.

## 8. Privacy and security requirements

Treat anonymity as a core requirement, not an optional feature.

-   Never require registration or personal details to submit or track a
    report.
-   Never store reporter names, emails, phone numbers, account IDs, IP
    addresses, or user-agent strings.
-   Do not expose reporter identity through any endpoint.
-   Do not expose internal database IDs or secret hashes in public
    responses.
-   Generate case codes using cryptographically secure randomness.
-   Protect moderator routes with authentication.
-   Validate and sanitize input appropriately.
-   Use parameterized ORM/database operations; do not build SQL queries
    by concatenating user input.
-   Handle missing records, invalid input, invalid status transitions,
    and unauthorized access with appropriate HTTP status codes.
-   Avoid logging report descriptions, evidence URLs, case codes,
    credentials, or other sensitive data.
-   Configure CORS only if required; do not use unrestricted CORS as a
    substitute for security.
-   Add a note in the README explaining that anonymity can be undermined
    by infrastructure-level access logs, reverse proxies, hosting
    providers, or external evidence links. Explain that production
    deployment must be configured to avoid retaining identifying
    metadata.
-   Do not claim that the system guarantees absolute anonymity.

## 9. API behavior and error handling

Use suitable HTTP methods and status codes, including:

-   `201 Created` --- report successfully submitted
-   `200 OK` --- successful reads and updates
-   `400 Bad Request` --- invalid workflow transition or malformed
    request where appropriate
-   `401 Unauthorized` --- moderator authentication missing or invalid
-   `404 Not Found` --- report/case code not found
-   `422 Unprocessable Entity` --- request validation failure
-   `500 Internal Server Error` --- unexpected server error, without
    exposing stack traces or secrets

Return consistent, understandable JSON error responses. Do not leak
database details, credentials, secret values, or internal stack traces.

## 10. Database design

Create SQLAlchemy models for at least:

### Report

-   Internal primary key
-   Case-code hash
-   Category
-   Description
-   Optional evidence URL
-   Status
-   Created timestamp
-   Updated timestamp

### StatusUpdate

-   Internal primary key
-   Related report ID
-   Status at the time of the update, if applicable
-   Short public update message
-   Created timestamp

Use a relationship between reports and status updates. Add appropriate
indexes for fields used in filtering and case-code lookup.

Do not create a reporter/user table. There are no reporter accounts in
this system.

## 11. Automated tests

Write automated tests for the important API behavior, including:

-   Submit a report successfully without authentication.
-   Reject missing or empty descriptions.
-   Reject invalid categories.
-   Accept an omitted evidence URL.
-   Reject malformed evidence URLs.
-   Return a unique case code for each report.
-   Track a report with a valid case code.
-   Reject an invalid case code.
-   Confirm public tracking does not expose internal IDs or private
    fields.
-   Confirm moderator routes reject unauthenticated requests.
-   Confirm moderator routes accept valid credentials.
-   List reports and filter by category/status.
-   Update a report status successfully.
-   Reject invalid status values and invalid status transitions.
-   Confirm a status update appears in the public tracking response.
-   Confirm terminal statuses cannot be changed through the normal
    workflow.

Use a separate test database and ensure tests do not modify the
developer's normal database.

## 12. Documentation

Create a useful `README.md` containing:

1.  Project overview and purpose.
2.  Features.
3.  Technology stack.
4.  Folder structure.
5.  Prerequisites.
6.  Setup and installation instructions.
7.  How to create and configure the `.env` file.
8.  How to start the FastAPI server.
9.  Swagger/OpenAPI documentation URL.
10. Every API endpoint, its purpose, authentication requirement, request
    body, and example response.
11. Example cURL requests for anonymous submission, case tracking,
    moderator login, listing/filtering reports, and updating status.
12. How anonymity is maintained and its limitations.
13. Status workflow and allowed transitions.
14. Important assumptions and design decisions.
15. How to run automated tests.
16. Production security considerations.

## 13. Running the application

The project should run with commands similar to:

``` bash
python -m venv venv
```

Windows:

``` bash
venv\Scripts\activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set appropriate local values.

Start the server:

``` bash
uvicorn app.main:app --reload
```

Open Swagger UI at:

`http://127.0.0.1:8000/docs`

Run tests:

``` bash
pytest -v
```

Ensure the database tables are created automatically for local
development, or document a simple database initialization command.

## 14. Acceptance criteria

The work is complete only when:

-   The backend starts successfully.
-   The database is initialized.
-   Anonymous users can submit reports without accounts.
-   Each submission returns a secure, unique case code.
-   A reporter can track a report using that code alone.
-   Moderators can authenticate and manage reports.
-   Moderators cannot see reporter identity information.
-   Status transitions and status updates work as documented.
-   Invalid and unauthorized requests are handled properly.
-   Automated tests pass.
-   Swagger/OpenAPI documentation is available.
-   README setup and API instructions are complete.
-   No frontend, UI, UX, or dashboard has been created.

## 15. Instructions to the coding agent

Before coding, inspect the existing workspace. If it already contains a
project, understand it and preserve useful working code rather than
overwriting files blindly.

Then: 1. Create or update the backend files. 2. Implement the database,
models, schemas, security, authentication, and routers. 3. Run the
application or perform import/startup checks. 4. Run the automated tests
and fix failures. 5. Check that the OpenAPI documentation loads. 6.
Update the README with commands that match the actual implementation. 7.
At the end, provide a concise summary of files created, endpoints
implemented, setup/run commands, test results, and any remaining
limitations.

Do not create any frontend or UI/UX components. Focus entirely on a
working, testable, privacy-conscious REST API.
