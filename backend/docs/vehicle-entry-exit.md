# Vehicle Entry and Exit Modules

Vehicle Entry and Exit provide the operational check-in and settlement workflow. Both are tenant-scoped, require `X-Company-ID`, a bearer token, and are visible only when the corresponding parking permissions are granted.

## Entry workflow

`POST /api/v1/vehicle-entries` accepts a normalized vehicle number, vehicle type, optional RFID/QR identifiers, owner/mobile details, optional captured vehicle image, and `advance_amount`.

- The server sets entry time in UTC and atomically increments a per-company/day counter to create a parking number (`P-YYYYMMDD-#####`) and token/card number (`T-YYYYMMDD-#####`).
- An active parking rate for the selected vehicle type is required. Its effective-dated slabs are copied into the entry as a rate snapshot, so later master-data changes cannot alter an in-progress visit.
- One active entry per company/vehicle is enforced by a partial unique index; RFID and QR identifiers are also checked against open entries.
- The optional image is validated as JPEG, PNG, or WebP (maximum 2 MB) and stored in tenant-scoped MongoDB GridFS. `GET /vehicle-entries/{entry_id}/image` is permission-protected.
- `advance_amount` is stored as BSON `Decimal128` and is applied automatically before exit payment is collected.

Entry receipts are available from `GET /vehicle-entries/{entry_id}/receipt` and include company receipt settings, the generated token/parking number, vehicle details, and advance collected.

## Exit workflow

`GET /api/v1/vehicle-exits/lookup` retrieves an **open** entry by one of `vehicle_number`, `card` (the generated token), `qr_code`, or `rfid`.

`GET /api/v1/vehicle-exits/{entry_id}/calculate` calculates the current settlement using the stored rate snapshot:

1. Duration is rounded up to whole minutes.
2. The matching duration slab supplies the parking charge and GST percentage.
3. GST, total, advance applied, and remaining balance are returned as decimal strings.

`POST /api/v1/vehicle-exits` completes the exit with `entry_id`, `paid_amount`, and one of `cash`, `upi`, or `card` when a payment is due. The service recalculates immediately before settlement, rejects overpayment or an unpaid balance, writes an immutable `vehicle_exits` record, appends a `payments` record, and closes the entry. A unique `entry_id` index prevents double settlement.

Exit receipts are available from `GET /vehicle-exits/{exit_id}/receipt` and include the charge, GST, total, advance adjustment, payment, and zero final balance.

## Persistence and indexes

| Collection | Purpose | Key indexes |
| --- | --- | --- |
| `vehicle_entries` | Open/closed parking session and immutable tariff snapshot | unique company/parking number, unique company/token, partial unique open company/vehicle, RFID/QR operational indexes |
| `vehicle_exits` | Immutable completed settlement | unique `entry_id`, company/exit timestamp, company/token |
| `payments` | Append-only exit payment | unique company/idempotency key, company/reference |
| `parking_counters` | Atomic tenant/day parking/token sequence | unique counter key |
| `vehicle_images.files` / `.chunks` | GridFS vehicle images | GridFS bucket indexes |

## Permissions and UI

| Screen/API area | Permissions |
| --- | --- |
| Vehicle entry | `parking_entry:show`, `parking_entry:save`, `parking_entry:details` |
| Vehicle exit | `parking_exit:show`, `parking_exit:save`, `parking_exit:details` |

The system Employee role receives these operational permissions by default. The React screens at `/vehicle-entry` and `/vehicle-exit` use large inputs, large primary buttons, responsive layouts, scanner-focus buttons for keyboard-wedge RFID/QR hardware, camera-capable image input, and a printer-targeted receipt dialog. The server remains authoritative for all financial calculations and validation.
