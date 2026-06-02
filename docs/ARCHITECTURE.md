# Architecture Deep Dive

## Request Lifecycle

Every HTTP request flows through this stack:

```
Client Request
      │
      ▼
CORSMiddleware          ← Validates Origin header
      │
      ▼
TenantMiddleware        ← Reads X-Tenant-ID → request.state.tenant_id
      │
      ▼
RateLimitMiddleware     ← Token bucket (60 req/min, Redis or in-process)
      │
      ▼
FastAPI Router          ← Path matching, dependency injection
      │
      ├─ get_db()       ← SQLAlchemy session (closes on response)
      ├─ get_current_user() ← Decode JWT, fetch User from DB
      └─ require_permission("scope") ← RBAC gate
      │
      ▼
Handler function        ← Business logic
      │
      ├─ DB read/write (SQLAlchemy ORM)
      ├─ Cache check/set (Redis or in-process dict)
      ├─ Background task enqueue (FastAPI BackgroundTasks)
      └─ audit.logger.log_action() (admin mutations)
      │
      ▼
Pydantic response model ← Serialisation, field validation
      │
      ▼
JSON Response
```

## Database Schema

```
users
  id, username, email, hashed_password, is_active, created_at

user_roles
  user_id (FK users), role (enum: admin/accountant/analyst/agent/viewer)

tax_records
  id, entity_name, entity_type, tax_year
  income, expenses, tax_due  (all Numeric(18,2))
  created_by (FK users), tenant_id (FK tenants, nullable)
  created_at, updated_at

tax_documents
  id, record_id (FK), doc_type, vault_key, checksum, created_at

rd_projects
  id, record_id (FK), name, description
  total_qre, estimated_credit, status, created_at

rd_expenses
  id, project_id (FK), category, description, amount, is_qualified

rd_documents
  id, project_id (FK), doc_type, content, validation_score, is_passing

analytics_snapshots
  id, snapshot_type, entity_name, payload (JSON), created_at

firms
  id, name, slug (unique), plan (starter/pro/enterprise), is_active

tenants
  id, firm_id (FK firms), name, external_id, is_active

audit_logs
  id, user_id (FK users), action, resource_type, resource_id
  tenant_id (FK tenants, nullable), ip_address, details (JSON text)
  created_at  ← no updated_at; immutable by design
```

## RBAC Permission Matrix

| Scope | admin | accountant | analyst | agent | viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| `filings:read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `filings:write` | ✓ | ✓ | | | |
| `forms:generate` | ✓ | ✓ | | | |
| `rd:write` | ✓ | ✓ | | | |
| `analytics:read` | ✓ | ✓ | ✓ | | |
| `documents:write` | ✓ | ✓ | | | |
| `users:manage` | ✓ | | | | |
| `audit:read` | ✓ | | | | |
| `integrations:use` | ✓ | ✓ | | | |
| `agent:chat` | ✓ | ✓ | ✓ | ✓ | |

## Caching Strategy

```
GET /tax/records/{id}
  │
  ├─ cache_get("record:{id}")  → HIT: return cached JSON
  │
  └─ MISS: query DB → cache_set("record:{id}", ttl=300) → return

PATCH /tax/records/{id}
  │
  ├─ Update DB
  └─ BackgroundTask: invalidate_record_cache(id)
       └─ cache_delete("record:{id}")
            └─ cache_clear_prefix("records:list")
```

Redis is used when `REDIS_URL` is set. Falls back to a module-level `dict` (`_local_cache`) so nothing breaks in local/test environments.

## JWT Authentication

Pure stdlib HMAC-HS256 — no `cryptography` or `python-jose` dependency:

```python
header  = base64url({"alg":"HS256","typ":"JWT"})
payload = base64url({"sub": username, "exp": unix_timestamp})
sig     = hmac_sha256(SECRET_KEY, header + "." + payload)
token   = header + "." + payload + "." + sig
```

`get_current_user()` first tries the internal JWT, then falls back to Supabase JWT passthrough if `SUPABASE_URL` is configured. This lets Supabase-auth clients use the same API without re-authenticating.

## IRC §41 Credit Engine Flow

```
analyze_project(project, expenses, prior_year_qre)
      │
      ├─ 1. classify_activity(description)
      │       └─ keyword match → ActivityType enum → is_qualified bool
      │
      ├─ 2. validate_project_documentation(project, docs)
      │       └─ scores 0-100 across: description, uncertainty_statement,
      │          alternatives_evaluated, experimental_results, doc count
      │          → ValidationResult(score, is_passing, gaps)
      │
      ├─ 3. score_all_expenses(expenses)
      │       └─ apply QUALIFICATION_RATES by ExpenseCategory
      │          → total_qre (Decimal)
      │
      └─ 4. calculate_credit(qre, prior_year_qre)
              └─ if prior_year_qre:
                   base = 0.5 × avg(prior_3yr)
                   credit = ASC_RATE (14%) × max(qre - base, 0)
                 else:
                   credit = ASC_RATE_STARTUP (6%) × qre
```

## Document Vault

Documents are stored on the filesystem under `DOCUMENT_VAULT_DIR`:

```
vault/
  {entity_name}/
    {record_id}/
      {doc_type}_{timestamp}.pdf
      {doc_type}_{timestamp}.pdf.meta.json   ← {checksum, size, created_at}
```

SHA-256 checksums are verified on every retrieve. The vault key stored in the DB is `{entity}/{record_id}/{filename}` — portable across storage backends.

## Rate Limiting

Token-bucket algorithm per IP address:

```
capacity  = RATE_LIMIT_BURST (default 10)
refill    = RATE_LIMIT_PER_MINUTE (default 60) tokens/minute
interval  = 1/refill seconds per token

On each request:
  now = time.monotonic()
  tokens += (now - last_request) × refill_rate
  tokens = min(tokens, capacity)
  if tokens >= 1:
      tokens -= 1  → allow
  else:
      return 429 with Retry-After: 60
```

State lives in Redis under `ratelimit:{ip}`. Falls back to `_local_buckets` dict for environments without Redis.
