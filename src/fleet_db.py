from typing import Dict, Any
import uuid
import time

from src.database import get_connection


def ensure_routes_populated(initial_routes: Dict[str, Any]):
    """Ensure the provided initial_routes exist in the DB. initial_routes is
    expected to be a dict of route_id -> object with origin, destination, capacity
    """
    conn = get_connection()
    try:
        for r_id, r in initial_routes.items():
            # r might be an object with origin/destination/capacity attributes
            if isinstance(r, dict):
                origin = r.get("origin")
                destination = r.get("destination")
                capacity = r.get("capacity")
            else:
                origin = getattr(r, "origin", None)
                destination = getattr(r, "destination", None)
                capacity = getattr(r, "capacity", None)

            if origin is None or destination is None or capacity is None:
                # skip malformed route entries
                continue

            existing = conn.execute("SELECT route_id FROM routes WHERE route_id = ?", (r_id,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO routes (route_id, origin, destination, capacity, booked_seats) VALUES (?, ?, ?, ?, 0)",
                    (r_id, origin, destination, int(capacity)),
                )
        conn.commit()
    finally:
        conn.close()


def get_all_routes():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM routes ORDER BY route_id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_route(route_id: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def reserve_seat(route_id: str, ticket_id: str | None = None) -> bool:
    """Attempt to reserve a seat atomically using BEGIN IMMEDIATE to acquire a write lock."""
    conn = get_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT capacity, booked_seats FROM routes WHERE route_id = ?", (route_id,)).fetchone()
        if not row:
            conn.execute("COMMIT")
            return False
        capacity = int(row["capacity"])
        booked = int(row["booked_seats"])
        if booked >= capacity:
            conn.execute("COMMIT")
            return False

        new_booked = booked + 1
        conn.execute("UPDATE routes SET booked_seats = ? WHERE route_id = ?", (new_booked, route_id))
        reservation_id = str(uuid.uuid4())[:8]
        placeholder_ticket_id = ticket_id or reservation_id
        conn.execute(
            "INSERT INTO reservations (reservation_id, ticket_id, route_id, created_at) VALUES (?, ?, ?, ?)",
            (reservation_id, placeholder_ticket_id, route_id, time.time()),
        )
        conn.execute("COMMIT")
        return True
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        conn.close()


def release_seat(route_id: str) -> bool:
    conn = get_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT booked_seats FROM routes WHERE route_id = ?", (route_id,)).fetchone()
        if not row:
            conn.execute("COMMIT")
            return False
        booked = int(row["booked_seats"])
        if booked <= 0:
            conn.execute("COMMIT")
            return False
        conn.execute("UPDATE routes SET booked_seats = ? WHERE route_id = ?", (booked - 1, route_id))
        conn.execute("COMMIT")
        return True
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False
    finally:
        conn.close()
