Integration & Feature changes implemented:

- Fleet persisted to SQLite via `routes` and `reservations` tables (created in `src/database.py`).
- DB-backed helper `src/fleet_db.py` provides atomic `reserve_seat` and `release_seat` using `BEGIN IMMEDIATE` transactions.
- Booking flow now uses DB-backed reservations; initial in-memory routes are populated into the DB at app startup.
- Added `/ticket/{ticket_id}/cancel` endpoint which cancels ticket and releases a seat (best-effort).
- Added `/conductor` route and `templates/conductor.html` to view route occupancy.
- Integration tests added: `tests/integration/test_fleet_booking.py`.

How to run tests:

```bash
pip install -r requirements.txt
pytest tests/integration/test_fleet_booking.py -q
```

Notes & next steps:

- For multi-process deployments, SQLite has limitations; migrating to PostgreSQL or adding an external locking service is recommended for heavy concurrency.
- You may want to backfill route capacities or change initial capacities in `src/app.py` to reflect production numbers.
