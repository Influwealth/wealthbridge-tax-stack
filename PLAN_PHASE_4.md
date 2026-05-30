# WealthBridge Tax Stack — Phase 4: Sovereign-Grade Tax Automation Platform

## Overview

Phase 4 expands the production-ready Phase 3 foundation into a full sovereign-grade tax
automation platform. Each wave is a self-contained, testable milestone. Waves execute
sequentially — later waves depend on earlier ones.

---

## Wave 1 — RBAC + Permission Engine

**Goal:** Fine-grained role-based access control enforced at the FastAPI dependency layer.

- Role matrix: `admin`, `accountant`, `business_owner`, `agent`, `auditor`
- Permission scopes: `filings:read`, `filings:write`, `filings:submit`, `filings:approve`,
  `expenses:read`, `expenses:approve`, `records:read`, `records:write`, `users:manage`, `audit:read`
- `Role` and `UserRole` models + Alembic migration `0002`
- `app/rbac.py` — permission matrix + `require_permission()` FastAPI dependency
- All existing routers updated to use permission guards
- Tests: role assignment, permission allow/deny, cross-role isolation

---

## Wave 2 — Additional IRS Form Engines

**Goal:** Expand form generation beyond 1065/1120/941.

- `irs_forms/form_schedule_c.py` — Sole proprietor profit/loss
- `irs_forms/form_w2.py` — Wage and Tax Statement
- `irs_forms/form_1099_nec.py` — Non-employee compensation
- `irs_forms/state/ny_it201.py`, `ca_540.py`, `tx_franchise.py` — state stubs
- `irs_forms/base.py` — shared base class + validation layer
- New `/forms/schedule-c`, `/forms/w2`, `/forms/1099-nec`, `/forms/state/{state}/{form}` endpoints
- `entity_type` extended to `sole_proprietor`, `contractor`, `employee`
- Tests for all new generators

---

## Wave 3 — PDF + XML E-File Layer

**Goal:** Generate, store, retrieve, and validate tax documents.

- `documents/pdf_filler.py` — PDF field-filling engine (pypdf)
- `documents/xml_efile.py` — IRS XML e-file stubs for 1120 and 1065
- `documents/vault.py` — document vault (local filesystem → S3/Supabase-ready interface)
- `app/routers/documents.py` — generate, store, retrieve, validate endpoints
- `documents/` directory with form templates
- Alembic migration `0003` — `tax_documents` table
- Tests: PDF generation, XML structure, vault store/retrieve

---

## Wave 4 — Redis + Caching + Task Queue

**Goal:** Production-grade performance layer and async job processing.

- Redis caching for form output, auth sessions, lookup tables
- `app/cache.py` — cache client + decorators
- Rate limiting middleware (slowapi or custom)
- Background task queue via FastAPI `BackgroundTasks` (upgrade path to Celery documented)
- `docker-compose.yml` updated with Redis service
- `.env.example` updated with `REDIS_URL`
- Tests: cache hit/miss, rate limit enforcement, background job execution

---

## Wave 5 — QRE-Agent Integration

**Goal:** Integrate a full R&D credit scoring engine as an internal service.

- `qre_agent/` module — project classifier, expense scorer, documentation validator
- Replaces the current `rd_plugin/rd_core.py` stub with full engine
- Alembic migration `0004` — `rd_projects`, `rd_expenses`, `rd_documents` tables
- `app/routers/rd.py` — project CRUD, expense classification, credit calculation, doc validation
- Permission-gated (accountant + admin only)
- Tests: classification, scoring, credit calculation, API endpoints

---

## Wave 6 — Caffeine Agent + Supabase Hybrid Architecture

**Goal:** Hybrid storage/auth with Supabase; Caffeine Agent as reasoning layer.

- `supabase/` module — client wrapper, schema migrations, row-level security helpers
- Auth extended to support Supabase JWT as alternative token source
- Storage layer abstraction: local → Supabase Storage / S3
- `caffeine_agent/` — reasoning layer wrapper (tool-calling interface)
- `app/routers/agent.py` — agent inference endpoint
- Environment config: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`
- Tests: Supabase auth passthrough, storage abstraction, agent endpoint

---

## Wave 7 — BI Dashboards + Forecasting

**Goal:** Tax analytics, credit optimization, and cashflow forecasting via API.

- `analytics/dashboard.py` — aggregate metrics per entity/year/type
- `analytics/forecasting.py` — cashflow + tax liability projections
- `analytics/credit_optimizer.py` — R&D + deduction optimization engine
- `app/routers/analytics.py` — dashboard, forecast, and optimization endpoints
- Alembic migration `0005` — `analytics_snapshots` table
- Tests: metric aggregation, forecast output shape, optimizer logic

---

## Wave 8 — Multi-Tenant Architecture

**Goal:** Firm → client hierarchy with full tenant isolation and audit logging.

- Alembic migration `0006` — `firms`, `tenants`, `audit_logs` tables
- `app/middleware/tenant.py` — tenant context extraction + injection
- All models extended with `tenant_id` FK
- `app/routers/admin.py` — firm/tenant management (admin only)
- `audit/logger.py` — immutable audit log writer
- Tests: cross-tenant isolation, audit log creation, firm hierarchy

---

## Completion Criteria

- All 8 waves implemented, committed, and pushed
- Full pytest suite green with ≥75% coverage
- Docker Compose stack starts cleanly end-to-end (db → migrate → redis → api)
- `/health` reports all dependencies healthy
- No hardcoded credentials anywhere in the codebase
- CI pipeline green on `claude/build-production-1F5Oe`
