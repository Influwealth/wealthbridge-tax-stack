# WealthBridge Tax Stack

> Production-grade tax management API for wealth management firms — built on FastAPI, PostgreSQL, Redis, and Claude AI.

---

## 🍋 What Is This? (Simple Version)

Imagine you run a lemonade stand. At the end of the year, the government says *"hey, you made money — you owe us some of it."* That's called **tax**. Now imagine instead of one lemonade stand you have hundreds of clients, each with their own businesses, their own receipts, their own rules. Keeping track of all that manually would be a nightmare.

**WealthBridge Tax Stack** is the software that does all of that automatically. It's like a super-smart accountant that lives inside a computer. It:

- 📋 **Keeps records** of every business's income and expenses
- 🧮 **Calculates** how much tax each business owes (automatically!)
- 📄 **Generates official IRS forms** (the forms you mail to the government)
- 🔬 **Finds tax credits** — special discounts the government gives if a company did research or invented something new
- 📊 **Predicts** how much tax a business will owe in future years
- 🔒 **Keeps everything secure** — only the right people can see the right information
- 🤖 **Has an AI assistant** you can talk to and ask tax questions

It's like a tax office that never sleeps, never makes arithmetic mistakes, and handles thousands of clients at once.

---

## 🏗️ What It Actually Does (Technical Version)

WealthBridge Tax Stack is a **REST API** — a set of web addresses (endpoints) that other apps can call to do tax-related work. It handles:

| Area | What it does |
|---|---|
| **Authentication** | JWT login, 5 RBAC roles, bcrypt password hashing |
| **Tax Records** | Full CRUD for income/expense records with auto tax calculation |
| **IRS Forms** | Generates 1065, 1120, 941, Schedule C, W-2, 1099-NEC, state forms |
| **R&D Tax Credit** | IRC §41 ASC engine — classifies expenses, scores documentation, calculates credit |
| **Document Vault** | Pure-Python PDF/XML generation, SHA-256 checksums, MeF e-file stubs |
| **Analytics** | Dashboard summaries, 5-year forecasts, credit optimizer (§41/§179/§199A/§163(j)) |
| **Multi-Tenant** | Firm → Tenant hierarchy, `X-Tenant-ID` middleware, cross-tenant isolation |
| **Audit Log** | Append-only immutable audit trail on all admin actions |
| **AI Agent** | Claude Sonnet (Caffeine Agent) for natural language tax Q&A |
| **Caching** | Redis-backed cache with in-process fallback, `@cached` decorator |
| **Rate Limiting** | Token-bucket middleware — 60 req/min per IP, Redis or in-process |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- (Optional) Redis — falls back to in-memory if unavailable

### 1. Clone and configure

```bash
git clone https://github.com/Influwealth/wealthbridge-tax-stack.git
cd wealthbridge-tax-stack
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD at minimum
```

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

This starts:
- **PostgreSQL 15** — database
- **Redis 7** — cache and rate limiting
- **migrate** — runs Alembic migrations then exits
- **api** — the FastAPI server on port 8000

### 3. Create your first admin user

```bash
docker-compose exec api python scripts/first_run.py
```

### 4. Get a token and start making requests

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "strongpassword123", "email": "alice@example.com"}'

# Login
curl -X POST http://localhost:8000/auth/token \
  -d "username=alice&password=strongpassword123"

# Use the token
curl http://localhost:8000/tax/records/ \
  -H "Authorization: Bearer <your_token_here>"
```

### 5. Explore the interactive docs

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser — all endpoints are documented and testable from the UI.

---

## 🗺️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │   Auth   │  │   Tax    │  │   IRS    │  │  R&D Credit   │  │
│  │  /auth   │  │ Records  │  │  Forms   │  │  qre_agent    │  │
│  │  JWT+    │  │  CRUD +  │  │ 1065/   │  │  IRC §41 ASC  │  │
│  │  RBAC    │  │  cache   │  │ 1120/941 │  │  classifier   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Analytics │  │ Document │  │  Multi-  │  │  Caffeine AI  │  │
│  │Dashboard │  │  Vault   │  │  Tenant  │  │  Agent        │  │
│  │Forecast  │  │ PDF/XML  │  │ Firm →   │  │  claude-      │  │
│  │Optimizer │  │ SHA-256  │  │ Tenant   │  │  sonnet-4-6   │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │          Middleware Stack (bottom-up execution)            │ │
│  │  CORSMiddleware → TenantMiddleware → RateLimitMiddleware   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────┬───────────────────┘
                       │                      │
              ┌────────▼──────┐     ┌─────────▼──────┐
              │  PostgreSQL   │     │     Redis       │
              │  (SQLAlchemy) │     │  Cache + Limits │
              │  Alembic mig. │     │  (in-proc. fallback)│
              └───────────────┘     └────────────────┘
```

### Directory Structure

```
wealthbridge-tax-stack/
├── app/                    # FastAPI application core
│   ├── auth.py             # JWT creation/validation, Supabase passthrough
│   ├── rbac.py             # Role-based access control (5 roles, 10 scopes)
│   ├── cache.py            # Redis cache layer + @cached decorator
│   ├── tasks.py            # Background tasks (doc gen, cache invalidation)
│   ├── models.py           # SQLAlchemy ORM models
│   ├── database.py         # Engine + get_db() dependency
│   ├── middleware/
│   │   ├── rate_limit.py   # Token-bucket rate limiter
│   │   └── tenant.py       # X-Tenant-ID header middleware
│   └── routers/            # One file per feature area
│       ├── auth.py         # POST /auth/register, /auth/token
│       ├── tax_records.py  # CRUD /tax/records/
│       ├── forms.py        # IRS form generation
│       ├── rd.py           # R&D project CRUD + credit calculation
│       ├── analytics.py    # Dashboards, forecasts, optimizer
│       ├── documents.py    # Document vault endpoints
│       ├── agent.py        # AI agent chat
│       ├── admin.py        # Firm/Tenant management, audit log
│       ├── users.py        # User management
│       └── integrations.py # External integrations
│
├── tax_capsule/            # Core tax engine
│   ├── tax_engine.py       # Entity-aware rate calculator
│   └── utils/
│       ├── schemas.py      # Pydantic v2 schemas (all DTOs)
│       └── logger.py       # JSON structured logging
│
├── qre_agent/              # IRC §41 R&D credit engine
│   ├── classifier.py       # 4-part test keyword classifier
│   ├── scorer.py           # QRE category qualification rates
│   ├── validator.py        # Documentation completeness scorer
│   └── engine.py           # ASC credit calculator
│
├── irs_forms/              # IRS form generators
│   ├── form_1065.py        # Partnership return
│   ├── form_1120.py        # Corporate return
│   ├── form_941.py         # Employer's quarterly
│   ├── form_schedule_c.py  # Sole proprietor P&L
│   ├── form_w2.py          # W-2 wages
│   ├── form_1099_nec.py    # 1099-NEC contractor
│   └── state/              # State tax stubs (NY, CA, TX)
│
├── caffeine_agent/         # Claude AI wrapper
│   ├── agent.py            # CaffeineAgent (claude-sonnet-4-6)
│   └── tools.py            # Tool schemas for Claude tool-use API
│
├── analytics/              # BI + forecasting
│   ├── dashboard.py        # Summary, entity, R&D dashboards
│   ├── forecasting.py      # Linear trend + IRC §6654 safe-harbor
│   └── credit_optimizer.py # §41/§179/§199A/§163(j) strategy ranking
│
├── audit/
│   └── logger.py           # Append-only audit log (log_action, get_audit_trail)
│
├── documents/
│   ├── pdf_filler.py       # Pure-Python PDF/1.4 writer (no C extensions)
│   ├── xml_efile.py        # MeF XML stubs for 1120/1065
│   └── vault.py            # SHA-256 checksum vault
│
├── supabase/               # Supabase hybrid layer
│   ├── auth.py             # JWT passthrough verification
│   ├── storage.py          # StorageBackend protocol (local/supabase)
│   └── rls_helpers.py      # Row-Level Security policy generators
│
├── alembic/                # Database migrations
│   └── versions/           # 0001 → 0006 migration chain
│
├── tests/                  # pytest suite (209 tests, 87% coverage)
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## 🔐 Authentication & Roles

Authentication uses **JWT Bearer tokens** (pure stdlib HMAC-HS256).

### Roles

| Role | Who | Key Permissions |
|---|---|---|
| `admin` | Firm administrators | Everything — user management, firms, tenants, audit log |
| `accountant` | CPA / tax preparer | Tax records CRUD, form generation, R&D projects, analytics |
| `analyst` | Read-only analyst | View tax records, analytics dashboards, reports |
| `agent` | AI/automation service | Read tax records, run AI agent queries |
| `viewer` | Client self-service | View own tax records only |

### Getting a Token

```bash
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=youruser&password=yourpassword
```

Returns `{"access_token": "...", "token_type": "bearer"}`. Pass as `Authorization: Bearer <token>` on all subsequent requests.

---

## 📡 Key API Endpoints

### Tax Records

```
POST   /tax/records/              Create a record (auto-calculates tax_due)
GET    /tax/records/              List records (filter by tax_year, pagination)
GET    /tax/records/{id}          Get single record
PATCH  /tax/records/{id}          Update record (recalculates tax_due)
DELETE /tax/records/{id}          Delete record
```

### IRS Forms

```
POST /forms/1065/{record_id}      Partnership Return (entity_type=partnership)
POST /forms/1120/{record_id}      Corporate Return (entity_type=corporation)
POST /forms/941/{record_id}       Employer Quarterly (entity_type=employer)
POST /forms/schedule-c/{id}       Sole Proprietor P&L
POST /forms/w2/{id}               W-2
POST /forms/1099-nec/{id}         1099-NEC contractor payment
POST /forms/state/{state}/{form}  State returns (ny/it201, ca/540, tx/franchise)
```

### R&D Tax Credit

```
POST   /rd/projects/              Create R&D project
GET    /rd/projects/              List projects
POST   /rd/projects/{id}/expenses     Add qualifying expense
POST   /rd/projects/{id}/documents    Submit documentation
POST   /rd/projects/{id}/calculate    Run IRC §41 ASC credit calculation
GET    /tax/records/{id}/rd-summary   Credit summary for a tax record
```

### Analytics

```
GET  /analytics/dashboard/summary           Firm-wide totals + by_entity_type
GET  /analytics/dashboard/entity/{name}     Multi-year history for one entity
GET  /analytics/dashboard/rd                R&D project aggregates
POST /analytics/forecast/tax-liability      5-year tax liability forecast
POST /analytics/forecast/cashflow           IRC §6654 quarterly payment schedule
POST /analytics/optimize/{record_id}        Credit strategy recommendations
```

### Admin (admin role only)

```
POST   /admin/firms                         Create firm
GET    /admin/firms                         List firms
POST   /admin/firms/{id}/tenants            Create tenant under firm
GET    /admin/firms/{id}/tenants            List tenants
DELETE /admin/firms/{id}/tenants/{tid}      Deactivate tenant
GET    /admin/audit-log                     Immutable audit trail (filterable)
```

### AI Agent

```
POST /agent/chat                            Natural language tax Q&A via Claude
GET  /agent/tools                           List available AI tools
GET  /agent/status                          Agent availability check
```

---

## 💰 R&D Tax Credit Engine

The `qre_agent` module implements the **IRC §41 Alternative Simplified Credit (ASC)** method:

```
Credit = 14% × (current QRE − 50% of average prior 3-year QRE)
Startup rate = 6% × current QRE (no prior year history)
```

### Expense qualification rates

| Category | Rate | Notes |
|---|---|---|
| `wages` | 100% | Direct research, supervision, support |
| `supplies` | 100% | Tangible consumables used in research |
| `computer_rental` | 100% | Cloud compute (AWS/GCP/Azure) for testing |
| `contract_research` | 65% | Third-party research (taxpayer retains rights) |
| `non_qualified` | 0% | G&A, routine ops, commercial evaluation |

### How it works

1. **Classifier** — keyword-based IRC §41 4-part test: checks for permitted purpose, technological nature, uncertainty elimination, process of experimentation
2. **Scorer** — applies qualification rates to each expense by category
3. **Validator** — scores documentation completeness 0–100 (passing threshold: 70)
4. **Engine** — runs ASC calculation with prior-year base period

---

## 🧪 Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_tax_records.py -v
```

**209 tests, 87% coverage.** Tests use SQLite in-memory — no Postgres or Redis required.

---

## 🐳 Docker

### Build and run

```bash
docker-compose up --build
```

### Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `db` | postgres:15-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Cache + rate limiting |
| `migrate` | (built) | — | Runs `alembic upgrade head` then exits |
| `api` | (built) | 8000 | FastAPI application |

### Health checks

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"3.0.0"}
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **Yes** | 64-char random hex for JWT signing |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection (falls back to in-process) |
| `ANTHROPIC_API_KEY` | No | Enables AI agent (Caffeine) |
| `SUPABASE_URL` | No | Enables Supabase auth passthrough |
| `SUPABASE_KEY` | No | Supabase service key |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `DOCUMENT_VAULT_DIR` | No | Path for document storage (default: `./vault`) |
| `ADMIN_USERNAME` | No | Bootstrap admin user for `first_run.py` |
| `ADMIN_PASSWORD` | No | Bootstrap admin password |

Generate a secure `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🏢 Multi-Tenant Architecture

WealthBridge supports a **Firm → Tenant** hierarchy for isolation between clients:

```
Firm (e.g. "Acme Tax Partners")
  └── Tenant (e.g. "Client Corp A")
  └── Tenant (e.g. "Client LLC B")
```

Pass `X-Tenant-ID: <tenant_id>` on requests to scope data. The middleware injects this into `request.state.tenant_id` for downstream filtering. All admin actions are automatically written to an append-only audit log.

---

## 📋 Alembic Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "describe your change"

# Roll back one step
alembic downgrade -1
```

Migration chain:
- `0001` — users, tax_records (base schema)
- `0002` — user_roles, RBAC tables
- `0003` — tax_documents (document vault)
- `0004` — rd_projects, rd_expenses, rd_documents
- `0005` — analytics_snapshots
- `0006` — firms, tenants, audit_logs; tenant_id on tax_records

---

## 🤖 AI Agent (Caffeine)

The Caffeine Agent wraps `claude-sonnet-4-6` and exposes it via `/agent/chat`. It has access to 5 tools it can call against the live API:

- `get_tax_record` — fetch a specific record
- `list_tax_records` — search/filter records
- `calculate_tax` — run tax calculation
- `get_rd_credit_summary` — fetch R&D credit analysis
- `get_form_data` — retrieve generated form data

If `ANTHROPIC_API_KEY` is not set, the agent returns a graceful unavailable response — nothing breaks.

---

## 🔒 Security Notes

- Passwords are hashed with `pbkdf2_sha256` (passlib)
- JWTs are signed with HMAC-HS256 using the `SECRET_KEY` env var
- Rate limiting: 60 requests/minute per IP (Redis-backed, in-process fallback)
- All secrets come from environment variables — never hardcoded
- Non-root Docker user (`appuser`, uid 1001)
- CORS origins are explicitly configured via `ALLOWED_ORIGINS`
- Audit log is append-only — no update or delete methods exist

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Write tests for your changes
4. Make sure all tests pass (`pytest tests/ -v`)
5. Open a pull request against `main`

Code style: follow existing patterns — FastAPI dependency injection, Pydantic v2 schemas, SQLAlchemy 2.0 ORM, no bare `except:` blocks.

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

*Built with FastAPI, SQLAlchemy, Alembic, Pydantic v2, Redis, passlib, and Claude AI.*
