# Employee Management Module

Employee Management is a tenant-scoped workforce directory with linked login accounts. API access is granted through the `employee:show`, `employee:save`, `employee:edit`, `employee:delete`, and `employee:details` permissions; super administrators bypass these checks.

## MongoDB design

### `employees`

```json
{
  "company_id": { "$oid": "..." },
  "user_id": { "$oid": "..." },
  "employee_id": "EMP-0042",
  "photo_url": "https://assets.example.com/employees/emp-0042.jpg",
  "name": "Mohan Singh",
  "gender": "male",
  "email": "mohan@example.com",
  "phone": "+919999999999",
  "address": { "line1": "7 Yard Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560064", "country_code": "IN" },
  "designation": "Parking Attendant",
  "username": "mohan.singh",
  "role_id": { "$oid": "..." },
  "salary": { "$numberDecimal": "45000.00" },
  "joining_date": { "$date": "2026-07-26T00:00:00Z" },
  "parking_location_id": { "$oid": "..." },
  "status": "active"
}
```

- Strict validation requires tenant/user links, identity fields, role, salary, joining date, and status.
- Unique indexes: `{ company_id: 1, employee_id: 1 }` and `{ company_id: 1, email: 1 }`.
- Operational indexes: `{ company_id: 1, status: 1, name: 1 }`, `{ company_id: 1, parking_location_id: 1, status: 1 }`, `{ company_id: 1, role_id: 1, status: 1 }`, and `{ company_id: 1, joining_date: -1 }`.
- User account usernames are protected by a sparse unique `{ username: 1 }` index. Passwords are Argon2-hashed and never returned.
- Salary is stored as BSON `Decimal128`; photo storage is represented by an object-storage URL.

On employee creation, a linked `users` document is created with the selected role. Role, email, username, password, and status changes are synchronized to that account. Deactivation disables the login and soft-deactivates the employee record.

## API

All endpoints use `/api/v1/employees`, a bearer token, and `X-Company-ID`.

| Operation | Permission | Endpoint |
| --- | --- | --- |
| List/search/filter/sort | `employee:show` | `GET /employees` |
| Options for roles and locations | `employee:show` | `GET /employees/options` |
| Create | `employee:save` | `POST /employees` |
| Details | `employee:details` | `GET /employees/{employee_id}` |
| Edit | `employee:edit` | `PATCH /employees/{employee_id}` |
| Deactivate | `employee:delete` | `DELETE /employees/{employee_id}` |
| Excel-compatible CSV export | `employee:details` | `GET /employees/export/excel` |
| PDF export | `employee:details` | `GET /employees/export/pdf` |

List and export filters support `search`, `status`, `gender`, `role_id`, `parking_location_id`, `sort_by`, and `sort_order`. List results also accept standard `page` and `limit` parameters.

## Responsive UI

The `/employees` screen has a responsive filter bar, sortable paginated table, employee create/edit form, details dialog, and permission-aware action buttons. It exposes Excel-compatible CSV export, PDF export, and browser print. Navigation is automatically hidden unless `employee:show` is present.
