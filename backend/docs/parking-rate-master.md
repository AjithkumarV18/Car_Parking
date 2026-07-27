# Parking Rate Master

Parking Rate Master is a tenant-scoped, effective-dated tariff catalogue. It covers the fixed vehicle classes Cycle, Bike, Car, Auto, Mini Bus, Bus, and Truck. Access is guarded by `rate:show`, `rate:save`, `rate:edit`, `rate:delete`, and `rate:details`; super administrators retain their existing authorization bypass.

## MongoDB design

### `parking_rates`

```json
{
  "company_id": { "$oid": "66a0f462b0e6b4aa11000001" },
  "vehicle_type": "truck",
  "duration_slabs": [
    { "from_minutes": 0, "to_minutes": 60, "amount": { "$numberDecimal": "120.00" }, "gst_percent": { "$numberDecimal": "18.00" } },
    { "from_minutes": 60, "to_minutes": 240, "amount": { "$numberDecimal": "300.00" }, "gst_percent": { "$numberDecimal": "18.00" } },
    { "from_minutes": 240, "to_minutes": null, "amount": { "$numberDecimal": "650.00" }, "gst_percent": { "$numberDecimal": "18.00" } }
  ],
  "effective_date": { "$date": "2026-08-01T00:00:00Z" },
  "status": "active"
}
```

- A strict collection validator enforces the tenant link, vehicle enum, non-empty slab array, BSON `Decimal128` amount/GST fields, effective date, and status (`draft`, `active`, or `inactive`).
- Application validation requires slabs to begin at minute `0`, be contiguous, have increasing finite end values, and only permits an open end on the final slab. Amount cannot be negative and GST must be between `0` and `100`.
- `{ company_id: 1, vehicle_type: 1, effective_date: 1 }` is unique, preserving one unambiguous rate version for each vehicle/effective date.
- `{ company_id: 1, status: 1, vehicle_type: 1, effective_date: -1 }` and `{ company_id: 1, effective_date: -1 }` support the management filters and history screens.

The effective date forms rate history: a later active rate for the same vehicle type does not overwrite an earlier record. A future parking transaction module can resolve the current tariff by selecting the latest active rate whose `effective_date` is no later than the entry date. This makes future price revisions auditable and avoids changing completed transaction totals.

## API

Every endpoint is under `/api/v1/parking-rates`, requires a bearer token and `X-Company-ID`, and is included in Swagger under **Parking Rate Master**.

| Operation | Permission | Endpoint |
| --- | --- | --- |
| List/search/filter/sort | `rate:show` | `GET /parking-rates` |
| Create | `rate:save` | `POST /parking-rates` |
| Details | `rate:details` | `GET /parking-rates/{rate_id}` |
| Edit | `rate:edit` | `PATCH /parking-rates/{rate_id}` |
| Deactivate | `rate:delete` | `DELETE /parking-rates/{rate_id}` |

List filters are `search`, `vehicle_type`, `status`, `effective_from`, `effective_to`, `sort_by`, `sort_order`, `page`, and `limit`. Inactive rows are excluded by default but remain available through `status=inactive` for audit and reactivation workflows.

## Responsive UI

`/parking-rates` provides a responsive filter bar, paginated rates table, permission-aware actions, and a create/edit dialog. The slab editor calculates each subsequent start minute from the preceding slab and only lets the user add another row after closing the preceding range. The backend remains the authoritative validator for all API clients.
