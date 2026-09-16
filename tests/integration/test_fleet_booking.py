from fastapi.testclient import TestClient
import os
import time

from src.app import app
from src import fleet_db, database


client = TestClient(app)


def reset_route_booked(route_id: str, capacity: int = None):
    conn = database.get_connection()
    try:
        if capacity is not None:
            conn.execute("UPDATE routes SET capacity = ? WHERE route_id = ?", (capacity, route_id))
        conn.execute("UPDATE routes SET booked_seats = 0 WHERE route_id = ?", (route_id,))
        conn.commit()
    finally:
        conn.close()


def test_booking_and_cancellation_flow():
    # ensure clean state
    reset_route_booked("R-101", capacity=2)

    # register and keep session
    r = client.post("/register", data={"email": "flow@example.com", "password": "pass", "name": "Flow"}, allow_redirects=False)
    assert r.status_code in (303,)

    before = fleet_db.get_route("R-101")
    initial = int(before["booked_seats"])

    # create booking
    r2 = client.post("/book", data={"passenger_name": "Alice", "passenger_age": "30", "route_id": "R-101"}, allow_redirects=False)
    assert r2.status_code == 303
    location = r2.headers["location"]
    ticket_id = location.rsplit("/", 1)[-1]

    after = fleet_db.get_route("R-101")
    assert int(after["booked_seats"]) == initial + 1

    # cancel the ticket
    r3 = client.post(f"/ticket/{ticket_id}/cancel", allow_redirects=False)
    assert r3.status_code == 303

    final = fleet_db.get_route("R-101")
    assert int(final["booked_seats"]) == initial


def test_double_booking_prevention():
    # set capacity to 1 to force contention
    reset_route_booked("R-101", capacity=1)

    client_a = TestClient(app)
    client_b = TestClient(app)

    # register both
    client_a.post("/register", data={"email": "a@example.com", "password": "p", "name": "A"}, allow_redirects=False)
    client_b.post("/register", data={"email": "b@example.com", "password": "p", "name": "B"}, allow_redirects=False)

    # first books
    r1 = client_a.post("/book", data={"passenger_name": "A Person", "passenger_age": "28", "route_id": "R-101"}, allow_redirects=False)
    assert r1.status_code == 303

    # second attempt should not increase booked seats beyond capacity
    r2 = client_b.post("/book", data={"passenger_name": "B Person", "passenger_age": "25", "route_id": "R-101"}, allow_redirects=False)

    # Check that booked_seats == capacity (1)
    current = fleet_db.get_route("R-101")
    assert int(current["booked_seats"]) <= 1
