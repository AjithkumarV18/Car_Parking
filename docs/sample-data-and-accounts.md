# Sample Data and Accounts

`backend/scripts/seed_demo.py` seeds a development-only tenant named **Demo Commercial Parking** with:

- Main Branch and North Yard parking location
- Bike, car, and truck rate masters
- Twelve visual parking slots (`A-01` through `A-12`)
- One active monthly pass (`MP-DEMO-00001`)
- Administrator and Super Administrator accounts

## Account configuration

| Account | Email variable | Password variable | System role |
| --- | --- | --- | --- |
| Admin | `SEED_ADMIN_EMAIL` | `SEED_ADMIN_PASSWORD` | Admin |
| Super admin | `SEED_SUPER_ADMIN_EMAIL` | `SEED_SUPER_ADMIN_PASSWORD` | Super Admin |

Local Compose defaults emails to `admin@demo.parking` and `superadmin@demo.parking`. Replace the development-only password defaults in `.env` before seeding. The script rejects `ENVIRONMENT=production`.

The Super Admin is flagged `is_super_admin=true`, so it can switch company contexts. The Admin remains tenant-scoped.

## Seed command

```powershell
docker compose --profile tools run --rm seed
```

For native execution, set both password variables, then run `python scripts/seed_demo.py` from `backend`.
