# Deployment Guide

## Production prerequisites

- Linux host with Docker Engine and Compose v2.
- A DNS `A` or `AAAA` record for the `SERVER_NAME` value.
- Firewall access to ports 80 and 443 only. Do not publish MongoDB or FastAPI ports.
- A GitHub Container Registry login on the host if release images are private.

## Configure production

1. Copy the templates without committing the generated files:

   ```bash
   cp .env.production.example .env.production
   cp backend/.env.production.example backend/.env.production
   ```

2. Set `SERVER_NAME`, generate unique MongoDB root/app credentials, and generate a 64-character-or-longer JWT secret. MongoDB credential characters must be URI-safe or percent-encoded because Compose constructs the connection URI.

3. Set `BACKEND_CORS_ORIGINS` and `ALLOWED_HOSTS` in `backend/.env.production` to the exact HTTPS hostname. Leave `DEBUG=false` and `DOCS_ENABLED=false`.

## TLS certificate bootstrap

The production Nginx image serves `/.well-known/acme-challenge/` on port 80 and expects certificates at:

```text
./certbot/conf/live/<SERVER_NAME>/fullchain.pem
./certbot/conf/live/<SERVER_NAME>/privkey.pem
```

Obtain a certificate before starting the HTTPS stack. One approach is to temporarily run a minimal HTTP-only Nginx/Certbot setup using the same `./certbot/www` webroot, then request the certificate:

```bash
docker run --rm -p 80:80 \
  -v "$PWD/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot -d parking.example.com --email ops@example.com --agree-tos --no-eff-email
```

Use a controlled bootstrap proxy if port 80 is already occupied. Schedule `certbot renew` and reload Nginx after renewal. Verify certificate ownership and permissions before continuing.

## Start or upgrade

For a source-based deployment:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
curl -fsS https://parking.example.com/api/v1/system/health
```

For a published release, set these image variables in `.env.production` or export them for the command:

```bash
BACKEND_IMAGE=ghcr.io/<owner>/parking-backend:v1.0.0
FRONTEND_IMAGE=ghcr.io/<owner>/parking-frontend:v1.0.0
NGINX_IMAGE=ghcr.io/<owner>/parking-nginx:v1.0.0
```

Then run `docker compose ... pull` followed by `docker compose ... up -d --remove-orphans`.

## Backup, recovery, and rollback

- Use the super-admin backup screen for tenant-level merge backups. Verify a restore only in a non-production environment first.
- Take regular encrypted MongoDB backups outside the Docker volume; tenant backups do not replace database disaster recovery.
- Keep the previous container image tag. Roll back by setting all three image variables to the prior tag and running `docker compose ... up -d`.
- Check `docker compose ... logs --tail=200 backend nginx` and `GET /api/v1/system/health` after each deployment.

## CI/CD

- `CI` runs linting, unit tests, frontend build, Docker builds, and Mongo-backed integration tests.
- `Release Images` publishes version-tagged backend, frontend, and Nginx images to GHCR.
- `Deploy Production` is a manually approved GitHub Environment workflow. Configure `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, and `DEPLOY_SSH_KEY` secrets, and ensure the host already contains the production Compose files and environment files.
