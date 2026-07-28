# Phase 1 Security and Health Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the first three Phase 1 hardening tasks without widening the change into Typed Settings or later roadmap work.

**Architecture:** Make three local changes at the existing module boundaries: sanitize password hashing logs in the auth module, validate the JWT environment secret at module load, and reduce the database health check to a connectivity probe with a metadata-free response.

**Tech Stack:** Python, FastAPI, SQLAlchemy, PyJWT, Passlib

## Global Constraints

- Do not run automated or manual tests.
- Do not add new dependencies.
- Do not introduce the Phase 1 Typed Settings module.
- Do not modify files outside `backend/app/auth/security.py`, `backend/app/db.py`, and `backend/app/main.py`.
- Do not run `git add`, `git commit`, or other Git write operations.
- Verification is limited to Python syntax compilation and final diff review.

---

### Task 1: Remove password-derived debug output and require JWT secret

**Files:**
- Modify: `backend/app/auth/security.py:12`
- Modify: `backend/app/auth/security.py:19-23`

**Interfaces:**
- Consumes: `JWT_SECRET` environment variable.
- Produces: Existing `hash_password(password: str) -> str`, `create_access_token(...) -> str`, and `decode_token(token: str) -> dict` interfaces without signature changes.

- [ ] **Step 1: Remove the development fallback**

Read `JWT_SECRET` without a default and reject a missing or empty value:

```python
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
  raise RuntimeError("JWT_SECRET is not set")
```

- [ ] **Step 2: Remove password hash debug output**

Keep the pre-hash and Passlib behavior, but remove both `print` calls:

```python
def hash_password(password: str) -> str:
  pre_hash = _sha256(password)
  return pwd_context.hash(pre_hash)
```

- [ ] **Step 3: Review the local diff**

Confirm that token algorithm, expiry, token payload, password verification, and function signatures are unchanged.

### Task 2: Replace database version query with a connectivity probe

**Files:**
- Modify: `backend/app/db.py:26-29`

**Interfaces:**
- Consumes: Existing SQLAlchemy `engine`.
- Produces: `db_ping() -> None`, raising the existing database exception if connectivity fails.

- [ ] **Step 1: Execute a lightweight probe**

Replace `SELECT version()` with `SELECT 1` and remove the returned version:

```python
def db_ping() -> None:
  with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
```

- [ ] **Step 2: Review the local diff**

Confirm that database URL normalization, engine construction, session setup, and `get_db()` are unchanged.

### Task 3: Remove database metadata from the health response

**Files:**
- Modify: `backend/app/main.py:51-54`

**Interfaces:**
- Consumes: `db_ping() -> None`.
- Produces: `GET /db-health` response `{"db": "ok"}` on a successful connection.

- [ ] **Step 1: Update the endpoint**

Call the connectivity probe without retaining a result:

```python
@app.get("/db-health")
def db_health():
  db_ping()
  return {"db": "ok"}
```

- [ ] **Step 2: Review the local diff**

Confirm that `/health`, CORS, routers, exception handlers, and scheduler lifecycle are unchanged.

### Task 4: Perform constrained verification

**Files:**
- Verify: `backend/app/auth/security.py`
- Verify: `backend/app/db.py`
- Verify: `backend/app/main.py`

**Interfaces:**
- Consumes: The three modified Python modules.
- Produces: Syntax-check evidence and a scoped final diff.

- [ ] **Step 1: Compile the modified files without importing them**

Run:

```powershell
python -m py_compile backend/app/auth/security.py backend/app/db.py backend/app/main.py
```

Expected: exit code `0` and no output. This checks syntax only and does not validate runtime behavior.

- [ ] **Step 2: Check whitespace errors**

Run:

```powershell
git diff --check -- backend/app/auth/security.py backend/app/db.py backend/app/main.py
```

Expected: exit code `0` and no output.

- [ ] **Step 3: Inspect the complete scoped diff**

Run:

```powershell
git diff -- backend/app/auth/security.py backend/app/db.py backend/app/main.py
```

Confirm all acceptance criteria from the approved design and explicitly report that runtime and API behavior remain untested.
