# Phase 1 Security and Health Hardening Design

## Scope

Implement the first three tasks from Phase 1 with minimal, local changes:

1. Remove password-hash debug output.
2. Remove the JWT `dev-secret` fallback and require `JWT_SECRET`.
3. Stop exposing the database version from the database health endpoint.

The broader Typed Settings work, global error contract, interface cleanup,
business workflow changes, and automated tests are outside this change.

## Design

### Password hashing

`backend/app/auth/security.py` will retain the existing SHA-256 pre-hash and
Passlib hashing behavior. The two debug `print` calls will be removed so that
password-derived data and related hash details are not written to application
logs.

### JWT configuration

`JWT_SECRET` will continue to come from the environment. The public
`dev-secret` default will be removed. If the variable is absent or empty,
loading the authentication security module will raise a clear `RuntimeError`.
Token creation and decoding will continue to use the validated secret and the
existing algorithm and expiration settings.

This intentionally does not introduce the Phase 1 Typed Settings module yet,
because doing so would widen the untested change across database, CORS,
scheduler, timezone, and AI configuration.

### Database health endpoint

`backend/app/db.py::db_ping()` will run `SELECT 1` instead of
`SELECT version()`. A successful connection will return no infrastructure
details.

`backend/app/main.py::db_health()` will call `db_ping()` and return only:

```json
{"db": "ok"}
```

Database connection failures will continue to propagate through the existing
FastAPI exception handling path. No new readiness/liveness split is included;
that remains a Phase 7 task.

## Files

- Modify `backend/app/auth/security.py`
- Modify `backend/app/db.py`
- Modify `backend/app/main.py`

## Verification constraints

Per user instruction, no automated or manual tests will be executed for this
change. Verification will be limited to:

- Python syntax compilation of the three modified files.
- Review of the final Git diff for scope and accidental changes.

Syntax compilation does not prove runtime behavior, environment integration,
database connectivity, or API correctness. Those remain unverified until
testing becomes available.

## Acceptance criteria

- Password hashing emits no debug output.
- There is no JWT fallback secret in production code.
- Missing or empty `JWT_SECRET` stops authentication module loading with a
  clear configuration error.
- `/db-health` exposes no PostgreSQL version or other database metadata.
- The database health query is a lightweight `SELECT 1`.
- No files outside the three listed backend modules are changed, excluding
  this design document and the later implementation plan.
