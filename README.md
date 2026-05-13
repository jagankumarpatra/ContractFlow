<div align="center">

# 📄 ContractFlow API

### Contract Lifecycle Management Backend — Python · FastAPI · PostgreSQL · AI

**A production-grade Contract Lifecycle Management (CLM) API.**  
Companies waste thousands of hours managing contracts manually — creation, review, approval, signing, and expiry tracking.  
ContractFlow automates the entire lifecycle with a clean REST API, enforced status workflows, AI-powered clause extraction, and async expiry alerts.

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [API Docs](#-api-documentation) · [Design Decisions](#-design-decisions) · [Tests](#-running-tests)

</div>

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🏢 **Multi-tenant** | Full company data isolation — JWT carries `company_id`, every query scoped to it |
| 🔐 **Auth** | Email/password login, bcrypt hashing, JWT tokens. First user per company = admin |
| 📄 **Contract Lifecycle** | State machine: `Draft → Under Review → Approved → Signed → Expired/Terminated` |
| 🤖 **AI Clause Extraction** | Claude API extracts parties, obligations, risky clauses, risk score (1-10) |
| ⚡ **Async Processing** | BackgroundTasks + Celery — AI analysis never blocks the API thread |
| 🔔 **Expiry Alerts** | Celery Beat runs daily, flags contracts expiring within 30 days |
| 🔍 **Search & Filter** | Search by title/party, filter by status, paginated listing |
| 📁 **File Upload** | Upload contract PDFs to AWS S3 (mock URL in dev — no S3 needed) |
| 🛡️ **Security** | CORS, Pydantic v2 validation on all inputs, structured error responses |
| 🧪 **27 Tests** | Auth, CRUD, state machine transitions, tenant isolation, search, AI trigger |

---

## 🛠 Tech Stack

| Layer | Technology | Why chosen |
|-------|-----------|-----------|
| Language | Python 3.11+ | Industry standard for B2B SaaS backends |
| Framework | FastAPI | Auto-generated OpenAPI docs, Pydantic v2, async support |
| Database | PostgreSQL + SQLAlchemy ORM | Relational — contracts need structured queries and ACID |
| Cache / Queue | Redis + Celery | Async job processing, Beat for scheduled tasks |
| Auth | JWT + bcrypt | Stateless, secure, battle-tested |
| AI | Anthropic Claude API | Contract clause extraction and risk analysis |
| Storage | AWS S3 | Contract PDF storage (mock in dev) |
| Validation | Pydantic v2 | Schema-first, type-safe request/response models |
| Testing | pytest + SQLite | 27 integration tests, zero external dependencies |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client / API Consumer                      │
│                     HTTP + Bearer JWT Token                       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                       │
│                                                                    │
│   ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│   │   Routers   │───▶│  Controllers │───▶│     Services       │  │
│   │  /auth      │    │  (endpoints) │    │  Business logic    │  │
│   │  /contracts │    └──────────────┘    └────────────────────┘  │
│   └─────────────┘                                                  │
│                                                                    │
│   Middleware: CORS · Pydantic Validation · JWT Auth · Errors      │
└─────────┬────────────────────────────────────┬────────────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────┐                  ┌──────────────────┐
│   PostgreSQL    │                  │     Redis        │
│                 │                  │                  │
│  companies      │                  │  Celery broker   │
│  users          │                  │  Task results    │
│  contracts      │                  └────────┬─────────┘
└─────────────────┘                           │
                                              ▼
                                   ┌──────────────────────┐
                                   │    Celery Worker      │
                                   │  + Celery Beat        │
                                   │  (scheduled tasks)    │
                                   └──────────┬────────────┘
                                              │
                              ┌───────────────┴──────────────┐
                              ▼                              ▼
                   ┌──────────────────┐         ┌──────────────────┐
                   │   Claude API     │         │     AWS S3       │
                   │ Clause extract   │         │  Contract files  │
                   │ Risk scoring     │         │  (mock in dev)   │
                   └──────────────────┘         └──────────────────┘
```

---

## 🔄 Flow Diagrams

### Flow 1 — User Registration & Login

```
Client                           FastAPI                    PostgreSQL
  │                                 │                           │
  │── POST /auth/register ─────────▶│                           │
  │   {name, email, password,       │── Check email exists ────▶│
  │    company_name}                │◀─ Not found ──────────────│
  │                                 │── Create Company ────────▶│
  │                                 │── Create User (admin) ───▶│
  │                                 │── bcrypt hash password    │
  │                                 │── Sign JWT token          │
  │◀── {token, user} ──────────────│                           │
  │                                 │                           │
  │── POST /auth/login ────────────▶│                           │
  │   {email, password}             │── Find user by email ────▶│
  │                                 │── bcrypt.verify()         │
  │                                 │── Sign JWT token          │
  │◀── {token, user} ──────────────│                           │
```

### Flow 2 — Contract Status Workflow (State Machine)

```
                    ┌─────────┐
                    │  DRAFT  │
                    └────┬────┘
                         │ submit for review
                         ▼
                 ┌──────────────┐
            ┌──▶│ UNDER_REVIEW │◀──┐
            │   └──────┬───────┘   │
   send back│          │ approve   │ send back
            │          ▼           │
            │      ┌──────────┐    │
            └──────│ APPROVED │────┘
                   └────┬─────┘
                        │ sign
                        ▼
                    ┌────────┐
                    │ SIGNED │
                    └────┬───┘
                         │ time passes
                         ▼
                    ┌─────────┐
                    │ EXPIRED │
                    └─────────┘

  Any stage ──TERMINATE──▶ TERMINATED
```

**Invalid transitions return HTTP 400** with the list of allowed next states.

### Flow 3 — AI Clause Extraction (Async)

```
Client             FastAPI              Background          Claude API
  │                   │                    │                    │
  │── POST /analyze ─▶│                    │                    │
  │                   │── Queue task ─────▶│                    │
  │◀── 200 OK ────────│  (instant)         │                    │
  │                   │                    │── Send contract ──▶│
  │                   │                    │   text + prompt    │
  │                   │                    │◀── JSON analysis ──│
  │                   │                    │                    │
  │                   │                    │── Save to DB       │
  │                   │                    │   contract.        │
  │                   │                    │   ai_analysis      │
  │                   │                    │                    │
  │── GET /contracts/{id} ──────────────▶  │                    │
  │◀── contract with ai_analysis ──────────│                    │
```

**API never waits for Claude.** Response is instant. Analysis appears on the contract when you fetch it.

### Flow 4 — Multi-Tenancy Isolation

```
Company A Token (JWT)          Company B Token (JWT)
company_id = "abc"             company_id = "xyz"
      │                               │
      ▼                               ▼
GET /contracts/                GET /contracts/
WHERE company_id = "abc"       WHERE company_id = "xyz"
      │                               │
      ▼                               ▼
[Contract A1, A2, A3]          [Contract B1, B2]

Company B trying to access Company A's contract:
GET /contracts/{contractA_id}
WHERE company_id = "xyz"  ──▶  404 Not Found
                               (not 403 — we don't reveal existence)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

```bash
# Easiest — Docker Desktop
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password --name pg postgres:14
docker run -d -p 6379:6379 --name redis redis:7
```

### Setup

```bash
# 1. Clone and install
git clone https://github.com/jagankumarpatra/ContractFlow.git
cd ContractFlow
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — only DATABASE_URL and SECRET_KEY required
```

### .env (minimum required)

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/contractflow
SECRET_KEY=any-random-string-at-least-32-chars-long
# Everything else is optional — works with mocks if not set
```

### Run

```bash
# Terminal 1 — API server
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker (optional, for async analysis)
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat scheduler (optional, for expiry alerts)
celery -A app.workers.celery_app beat --loglevel=info
```

**Visit http://localhost:8000/docs for interactive Swagger UI** 📖

---

## 📡 API Documentation

**Base URL:** `http://localhost:8000/api/v1`  
**Auth:** All 🔒 routes require `Authorization: Bearer <token>` header  
**Format:** All requests/responses are `application/json`

---

### 🔐 Authentication

#### `POST /auth/register` — Register new user + company

```json
// Request body
{
  "name": "Jagan Kumar",
  "email": "jagan@company.com",
  "password": "securepass123",
  "company_name": "Runo Inc"
}
```

```json
// 201 Response
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "Jagan Kumar",
    "email": "jagan@company.com",
    "role": "admin",
    "company_id": "uuid",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

> First user in a company gets `role: "admin"`. Subsequent users get `role: "member"`.

---

#### `POST /auth/login` — Login

```json
// Request
{ "email": "jagan@company.com", "password": "securepass123" }

// 200 Response — same as register
{ "access_token": "eyJ...", "token_type": "bearer", "user": {...} }
```

**Error responses:**
- `401` — Invalid email or password
- `422` — Validation error (missing fields, invalid email format)

---

### 📄 Contracts 🔒

#### `POST /contracts/` — Create contract

```json
// Request
{
  "title": "Software Development Agreement",
  "contract_type": "service_agreement",
  "party_a": "Client Corp",
  "party_b": "Dev Agency Ltd",
  "description": "Annual software development retainer",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2025-01-01T00:00:00Z",
  "contract_text": "This Software Development Agreement is entered into between..."
}
```

```json
// 201 Response
{
  "id": "uuid",
  "title": "Software Development Agreement",
  "contract_type": "service_agreement",
  "status": "draft",
  "party_a": "Client Corp",
  "party_b": "Dev Agency Ltd",
  "description": "Annual software development retainer",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2025-01-01T00:00:00Z",
  "file_url": null,
  "file_name": null,
  "ai_analysis": null,
  "ai_analyzed_at": null,
  "company_id": "uuid",
  "created_by_id": "uuid",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

> `contract_type` options: `nda` | `service_agreement` | `employment` | `vendor` | `partnership` | `other`  
> If `contract_text` is provided, AI analysis starts automatically in the background.

---

#### `GET /contracts/` — List contracts

```
GET /contracts/?status=draft&search=ACME&page=1&limit=20
```

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `status` | string | — | Filter by status |
| `search` | string | — | Search title, party_a, party_b |
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Max 100 |

```json
// 200 Response
{
  "contracts": [ ...ContractResponse... ],
  "total": 47,
  "page": 1,
  "limit": 20
}
```

---

#### `GET /contracts/{id}` — Get single contract

```json
// 200 Response — full contract with AI analysis if available
{
  "id": "uuid",
  "status": "under_review",
  "ai_analysis": {
    "parties": ["Client Corp", "Dev Agency Ltd"],
    "contract_summary": "Annual software development retainer agreement...",
    "key_dates": { "start_date": "2024-01-01", "end_date": "2025-01-01" },
    "key_obligations": [
      "Dev Agency must deliver monthly sprint reports",
      "Client must pay invoices within 30 days"
    ],
    "risky_clauses": [
      "Section 8.2: No IP ownership clause for client"
    ],
    "payment_terms": "Net 30 days",
    "governing_law": "Laws of India",
    "risk_score": 5,
    "risk_level": "medium",
    "recommendations": ["Add explicit IP assignment clause"]
  }
}
```

- `404` — Contract not found (or belongs to another company)

---

#### `PATCH /contracts/{id}` — Update contract details

```json
// Request — all fields optional
{
  "title": "Updated Agreement Title",
  "party_b": "New Agency Name",
  "end_date": "2025-06-01T00:00:00Z"
}
// 400 — Cannot edit a signed contract
```

---

#### `PATCH /contracts/{id}/status` — Update status

```json
// Request
{ "status": "under_review" }

// 200 — Contract with updated status
// 400 — Invalid transition, with message:
{
  "detail": "Cannot transition from 'draft' to 'signed'. Allowed: ['under_review', 'terminated']"
}
```

**Valid transitions:**

| From | To (allowed) |
|------|-------------|
| `draft` | `under_review`, `terminated` |
| `under_review` | `approved`, `draft`, `terminated` |
| `approved` | `signed`, `under_review`, `terminated` |
| `signed` | `expired`, `terminated` |
| `expired` | *(none)* |
| `terminated` | *(none)* |

---

#### `POST /contracts/{id}/analyze` — Trigger AI analysis

```
POST /contracts/{uuid}/analyze

// 200 — Returns contract immediately
// Analysis runs in background, appears on next GET
```

**AI analysis output structure:**

```json
{
  "parties": ["string"],
  "contract_summary": "string",
  "key_dates": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "notice_period": "string"
  },
  "key_obligations": ["string"],
  "risky_clauses": ["string"],
  "payment_terms": "string",
  "governing_law": "string",
  "termination_conditions": ["string"],
  "risk_score": 1,
  "risk_level": "low | medium | high",
  "recommendations": ["string"]
}
```

> Without `ANTHROPIC_API_KEY`, returns a realistic mock with the same structure.

---

#### `POST /contracts/{id}/upload` — Upload contract file

```
POST /contracts/{uuid}/upload
Content-Type: multipart/form-data

file: <binary PDF or text file>

// 200 — Contract with file_url and file_name populated
```

---

#### `DELETE /contracts/{id}` — Delete contract

```
DELETE /contracts/{uuid}

// 204 — Deleted successfully
// 400 — Can only delete draft or terminated contracts
// 404 — Not found
```

---

### ❌ Error Response Format

All errors return a consistent shape:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (validation, invalid transition) |
| `401` | Unauthorized (invalid/expired token) |
| `403` | Forbidden (missing token) |
| `404` | Resource not found |
| `409` | Conflict (duplicate email) |
| `422` | Unprocessable entity (Pydantic schema error) |
| `500` | Internal server error |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate_email PASSED
tests/test_auth.py::test_register_second_user_is_member PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_wrong_password PASSED
tests/test_auth.py::test_login_nonexistent_user PASSED
tests/test_auth.py::test_protected_route_without_token PASSED
tests/test_auth.py::test_protected_route_with_invalid_token PASSED
tests/test_contracts.py::test_create_contract PASSED
tests/test_contracts.py::test_create_contract_minimal PASSED
tests/test_contracts.py::test_create_contract_unauthenticated PASSED
tests/test_contracts.py::test_get_contract PASSED
tests/test_contracts.py::test_get_nonexistent_contract PASSED
tests/test_contracts.py::test_list_contracts PASSED
tests/test_contracts.py::test_list_contracts_pagination PASSED
tests/test_contracts.py::test_list_contracts_filter_by_status PASSED
tests/test_contracts.py::test_list_contracts_search PASSED
tests/test_contracts.py::test_update_contract PASSED
tests/test_contracts.py::test_valid_status_transition PASSED
tests/test_contracts.py::test_invalid_status_transition PASSED
tests/test_contracts.py::test_full_status_workflow PASSED
tests/test_contracts.py::test_delete_draft_contract PASSED
tests/test_contracts.py::test_cannot_delete_signed_contract PASSED
tests/test_contracts.py::test_tenant_isolation PASSED
tests/test_contracts.py::test_ai_analysis_trigger PASSED
tests/test_health.py::test_health PASSED
tests/test_health.py::test_root PASSED

27 passed in 7.68s
```

Tests use **SQLite in-memory** — no PostgreSQL or Redis needed to run the test suite.

---

## 🧠 Design Decisions

### 1. Multi-tenancy via service-layer filtering
Every query in `contract_service.py` filters by `company_id` extracted from the JWT. This means:
- No router-level middleware magic
- Easy to audit — grep `company_id` to see every access-controlled query
- 404 (not 403) on cross-tenant access — doesn't reveal resource existence to attackers

### 2. State machine with explicit transition map
```python
VALID_TRANSITIONS = {
    ContractStatus.DRAFT: [UNDER_REVIEW, TERMINATED],
    ContractStatus.UNDER_REVIEW: [APPROVED, DRAFT, TERMINATED],
    ...
}
```
Invalid transitions return a 400 with the allowed next states — better DX than letting DB constraints catch it.

### 3. BackgroundTasks over blocking AI calls
Claude API takes 2-5 seconds. Blocking the request thread means:
- Timeouts under load (Gunicorn default 30s)
- Thread pool exhaustion
- Poor p99 latency

`BackgroundTasks` offloads to a thread pool — API responds in <50ms.

### 4. bcrypt directly (not passlib)
`passlib` has a known incompatibility with newer `bcrypt` versions in Python 3.12. Using `bcrypt` directly avoids version hell and reduces dependencies.

### 5. SQLite for tests, PostgreSQL for production
Engine is monkey-patched in `conftest.py` before any app imports. Tests run with zero external dependencies — no Docker required for CI.

### 6. Pydantic v2 `model_config = {"from_attributes": True}`
Replaces v1's `orm_mode = True`. Allows direct serialization from SQLAlchemy ORM objects without manual `.dict()` calls.

---

## 📂 Project Structure

```
contractflow/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py         # /auth/register, /auth/login
│   │       │   └── contracts.py    # all /contracts/* routes
│   │       └── router.py           # mounts all endpoint routers
│   ├── core/
│   │   ├── config.py               # Pydantic Settings — reads .env
│   │   ├── security.py             # bcrypt hash/verify, JWT sign/decode
│   │   └── exceptions.py           # AppError subclasses (404, 401, etc.)
│   ├── db/
│   │   └── base.py                 # SQLAlchemy engine, SessionLocal, get_db
│   ├── models/
│   │   ├── company.py              # Company ORM model
│   │   ├── user.py                 # User ORM model + UserRole enum
│   │   └── contract.py             # Contract ORM model + status/type enums
│   ├── schemas/
│   │   ├── company.py              # Pydantic request/response schemas
│   │   ├── user.py                 # UserRegister, UserLogin, TokenResponse
│   │   └── contract.py             # ContractCreate, Update, StatusUpdate, Response
│   ├── services/
│   │   ├── auth_service.py         # register_user, login_user
│   │   ├── contract_service.py     # CRUD + state machine transitions
│   │   ├── ai_service.py           # Claude API + mock fallback
│   │   └── s3_service.py           # S3 upload + mock URL fallback
│   ├── utils/
│   │   └── deps.py                 # get_current_user, require_admin FastAPI deps
│   ├── workers/
│   │   ├── celery_app.py           # Celery app config + Beat schedule
│   │   └── tasks.py                # analyze_contract_task, check_expiring_contracts
│   └── main.py                     # FastAPI app, CORS, router mount
├── tests/
│   ├── conftest.py                 # SQLite engine patch, all shared fixtures
│   ├── test_auth.py                # 8 auth tests
│   ├── test_contracts.py           # 17 contract tests
│   └── test_health.py              # 2 health tests
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 🗺 Roadmap

- [x] Multi-tenant company + user auth with role system
- [x] Contract CRUD with full lifecycle state machine
- [x] AI clause extraction and risk scoring
- [x] Async background job processing
- [x] Contract search and filtering
- [x] File upload with S3
- [x] 27 integration tests (no external dependencies)
- [ ] Alembic database migrations
- [ ] Email notifications on status change (SES)
- [ ] Role-based access (viewer read-only)
- [ ] Contract templates library
- [ ] Bulk contract import (CSV)
- [ ] Docker Compose for one-command setup
- [ ] GitHub Actions CI pipeline

---

## 👨‍💻 Author

**Jagan Kumar Patra** — Backend Engineer  

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat&logo=linkedin)](https://www.linkedin.com/in/)
[![GitHub](https://img.shields.io/badge/GitHub-jagankumarpatra-181717?style=flat&logo=github)](https://github.com/jagankumarpatra)

---

<div align="center">
Built to demonstrate production Python backend engineering.<br/>
FastAPI · PostgreSQL · Redis · Celery · Claude AI · Multi-tenancy · 27 Tests
</div>
