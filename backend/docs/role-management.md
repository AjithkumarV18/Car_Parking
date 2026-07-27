# Role Management Module

Role Management provides a permission matrix for the five standard actions: **Show**, **Save**, **Edit**, **Delete**, and **Details**. It is available only to a super administrator and requires the standard `Authorization` bearer token plus `X-Company-ID` tenant header.

## Defaults

The database startup initializer seeds immutable system templates:

| Role | Purpose |
| --- | --- |
| Super Admin | Platform-level access across all companies; enforced by `is_super_admin` on the user identity. |
| Admin | Tenant administrator template with dashboard and company read access. |
| Owner | Owner-facing template with dashboard and company details access. |
| Employee | Employee template with dashboard visibility. |
| Viewer | Minimal authentication profile and dashboard access. |

System templates can be viewed but not edited or deleted. Super administrators can create, edit, and soft-delete tenant-specific roles. A role cannot be deleted while it is assigned to an active user.

## Database

### `permissions`

```json
{ "key": "company:edit", "name": "Edit companies", "module": "company", "action": "edit", "status": "active" }
```

- Unique index: `{ key: 1 }`.
- The `module` and `action` values render the frontend matrix.
- Current catalogue includes `company:*`, `role:*`, `dashboard:show`, and `auth:self_read` permissions.

### `roles`

```json
{
  "scope": "company",
  "company_id": { "$oid": "..." },
  "code": "yard_operator",
  "name": "Yard Operator",
  "description": "Can view and edit assigned operations.",
  "permission_ids": [{ "$oid": "..." }],
  "is_system": false,
  "status": "active"
}
```

- Strict validator requires `scope`, `code`, `permission_ids`, and `status`.
- Unique index: `{ scope: 1, company_id: 1, code: 1 }`.
- System roles have `scope: "system"`, `company_id: null`, and `is_system: true`.
- Company roles have `scope: "company"`, and are only visible inside their tenant context.

## API

| Operation | Endpoint |
| --- | --- |
| List permission catalogue | `GET /api/v1/roles/permissions` |
| List system + current-company roles | `GET /api/v1/roles` |
| Create company role | `POST /api/v1/roles` |
| View role details | `GET /api/v1/roles/{role_id}` |
| Edit company role | `PATCH /api/v1/roles/{role_id}` |
| Soft-delete company role | `DELETE /api/v1/roles/{role_id}` |

Swagger documents the bearer security scheme and `X-Company-ID` header at `/docs`.

## Permission enforcement

`require_permissions(...)` resolves the user’s role IDs, active role definitions, and active permissions from MongoDB during every protected request. It then validates all required permissions. This makes role changes effective immediately on the backend, without waiting for an access token’s embedded permission snapshot to expire.

The shared frontend `PermissionGate` uses the token permission claims to conditionally render navigation. Therefore menus such as **Companies** and **Roles** automatically remain hidden unless the corresponding `company:show` or `role:show` permission is available; super administrators bypass the gate.
