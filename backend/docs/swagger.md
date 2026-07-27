# Swagger and OpenAPI

Interactive Swagger UI is exposed at `/docs` when `DOCS_ENABLED=true`. The OpenAPI JSON document is available at `/api/v1/openapi.json`.

Generate a checked-in snapshot when an external API gateway or client generator needs one:

```bash
python scripts/export_openapi.py
```

## Authentication

1. Call `POST /api/v1/auth/login` with the required `X-Company-ID` header.
2. Copy `data.access_token` from the common response envelope.
3. In Swagger, click **Authorize** and enter the token for the Bearer security scheme.
4. Keep sending `X-Company-ID` for every tenant endpoint.

Example login payload:

```json
{
  "email": "admin@demo.parking",
  "password": "your-strong-password",
  "remember_me": false
}
```

## API contract

All success and failure responses use the same envelope:

```json
{
  "success": true,
  "message": "OK",
  "data": {},
  "error": null,
  "requestId": "request-correlation-id"
}
```

Validation failures return HTTP 422, authentication failures 401, permission failures 403, missing data 404, conflicts 409, and unavailable database dependencies 503. Production sets `DOCS_ENABLED=false`; expose documentation only through a protected internal environment.
