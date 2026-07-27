# Testing Guide

## Test tiers

| Tier | Scope | Command |
| --- | --- | --- |
| Unit | Models, security, service calculations, OpenAPI, and seed validation | `python -m pytest -m "not integration"` |
| Integration | FastAPI middleware, JWT login, RBAC, and MongoDB persistence | `python -m pytest -m integration` |
| Frontend quality | Type checking, ESLint, and production bundle | `npm run lint && npm run build` |

Unit tests do not require MongoDB. Integration tests are opt-in and refuse to run unless `MONGODB_DATABASE` ends in `_test`.

## Run integration tests locally

```powershell
docker compose up mongodb -d
$env:RUN_INTEGRATION_TESTS = '1'
$env:MONGODB_URI = 'mongodb://localhost:27017'
$env:MONGODB_DATABASE = 'parking_integration_test'
Set-Location backend
python -m pytest -m integration
```

GitHub Actions runs both tiers: unit checks in the `quality` job and Mongo-backed API tests in the `integration` job.
