from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_home_page():
    response = client.get("/")
    assert response.status_code == 200

def test_user_registration_login_logout_and_dashboard():
    # 1. Register a new user
    reg_res = client.post(
        "/register",
        data={"name": "Melat", "email": "melat@example.com", "password": "securepassword123"},
        follow_redirects=False
    )
    assert reg_res.status_code in [200, 303]

    # 2. Log in with credentials
    login_res = client.post(
        "/login",
        data={"email": "melat@example.com", "password": "securepassword123"},
        follow_redirects=False
    )
    assert login_res.status_code in [200, 303]

    # 3. Access protected dashboard
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200

    # 4. Log out
    logout_res = client.get("/logout", follow_redirects=False)
    assert logout_res.status_code in [200, 303]

def test_dashboard_redirects_unauthenticated():
    # Fresh unauthenticated client should bounce from dashboard
    unauth_client = TestClient(app)
    res = unauth_client.get("/dashboard", follow_redirects=False)
    assert res.status_code in [302, 303, 307]

def test_booking_and_ticket_lifecycle_flow():
    # 1. Book ticket
    book_res = client.post(
        "/book",
        data={
            "passenger_name": "Melat Wolde",
            "passenger_age": 25,
            "route_id": "R-101",
            "is_peak": "true",
            "is_frequent": "true"
        },
        follow_redirects=False
    )
    assert book_res.status_code == 303
    ticket_url = book_res.headers["location"]
    ticket_id = ticket_url.split("/")[-1]

    # 2. View ticket page
    view_res = client.get(ticket_url)
    assert view_res.status_code == 200

    # 3. Pay for ticket
    pay_res = client.post(f"/ticket/{ticket_id}/pay", follow_redirects=False)
    assert pay_res.status_code == 303

    # 4. Conductor scan
    scan_res = client.post(f"/ticket/{ticket_id}/scan", follow_redirects=False)
    assert scan_res.status_code == 303

def test_booking_invalid_age_error_handling():
    response = client.post(
        "/book",
        data={
            "passenger_name": "Invalid Passenger",
            "passenger_age": -5,
            "route_id": "R-101"
        }
    )
    assert response.status_code == 200
    assert "Invalid age" in response.text

def test_ticket_not_found_branches():
    assert client.get("/ticket/non-existent-id").status_code == 404
    assert client.post("/ticket/non-existent-id/pay").status_code == 404
    assert client.post("/ticket/non-existent-id/scan").status_code == 404
