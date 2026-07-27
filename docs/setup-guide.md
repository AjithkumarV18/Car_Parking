# Setup Guide

## Prerequisites

- Docker Desktop with Compose v2, or Python 3.12+ and Node 22+ for native development.
- A modern browser with camera access for QR and webcam capture.

## Docker local development

1. Create local environment files:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item backend/.env.example backend/.env
   Copy-Item frontend/.env.example frontend/.env
   ```

2. Change the four `SEED_*` passwords in `.env` after copying it. They must be at least 12 characters.

3. Start the stack and load non-production sample data:

   ```powershell
   docker compose up --build -d
   docker compose --profile tools run --rm seed
   ```

4. Open `http://localhost:3000`. The seed output includes the `X-Company-ID` needed for the login screen and API calls.

## Native development

Start MongoDB with `docker compose up mongodb -d`, then use two terminals:

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

```powershell
Set-Location frontend
npm ci
npm run dev
```

Run the seed script after exporting credentials:

```powershell
$env:SEED_ADMIN_PASSWORD = 'Use-A-Strong-Password1!'
$env:SEED_SUPER_ADMIN_PASSWORD = 'Use-Another-Strong-Password1!'
Set-Location backend
python scripts/seed_demo.py
```

The script is idempotent and preserves an existing seeded user's password hash. It is intentionally disabled in production.
