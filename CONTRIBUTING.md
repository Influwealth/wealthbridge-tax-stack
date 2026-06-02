# Contributing to WealthBridge Tax Stack

Thanks for wanting to help! Here's how to get set up and what to keep in mind.

## Setup

```bash
git clone https://github.com/Influwealth/wealthbridge-tax-stack.git
cd wealthbridge-tax-stack
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest tests/ -v   # should be 209 passing
```

## Making Changes

- **One feature per PR** — small, focused changes are easier to review
- **Write tests first** — every new endpoint or module needs test coverage
- **Run the full suite before pushing** — `pytest tests/ -v --cov=.`
- **No secrets in code** — all config via environment variables

## Code Conventions

| Thing | Convention |
|---|---|
| Schemas | Pydantic v2 with `ConfigDict(from_attributes=True)` |
| DB access | SQLAlchemy 2.0 ORM via `get_db()` dependency |
| Auth | `Depends(require_permission("scope:action"))` |
| Money fields | `Numeric(18,2)` — never `Float` |
| Logging | `from tax_capsule.utils.logger import get_logger` |
| Comments | Only when the WHY is non-obvious |

## Branch Naming

```
feat/description     — new feature
fix/description      — bug fix
docs/description     — documentation only
refactor/description — no behaviour change
```

## Tests

Tests use **SQLite in-memory** — no Postgres or Redis needed:

```bash
pytest tests/test_tax_records.py -v        # single file
pytest tests/ -v -k "test_auth"            # filter by name
pytest tests/ --cov=. --cov-report=html    # coverage report → htmlcov/
```

The `conftest.py` autouse fixture clears rate-limit and cache state between every test — do not add module-level state without a corresponding cleanup.

## PR Checklist

- [ ] All 209+ existing tests still pass
- [ ] New tests cover the happy path and key error cases
- [ ] No new secrets or hardcoded credentials
- [ ] `Numeric(18,2)` used for all monetary fields
- [ ] Audit log called for any admin write operations
