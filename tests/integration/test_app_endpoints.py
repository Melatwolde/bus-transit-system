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


def test_pay_ticket_with_chapa_gateway(monkeypatch):
    from src.app import tickets_db

    class MockResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        text = '{"status":"success","message":"Hosted Link","data":{"checkout_url":"https://checkout.chapa.co/test-checkout"}}'

        def json(self):
            import json
            return json.loads(self.text)

    monkeypatch.setattr("requests.post", lambda url, json=None, headers=None, timeout=None: MockResponse())

    # 1. Book a ticket
    book_res = client.post(
        "/book",
        data={
            "passenger_name": "Chapa Passenger",
            "passenger_age": 30,
            "route_id": "R-101",
        },
        follow_redirects=False
    )
    assert book_res.status_code == 303
    ticket_id = book_res.headers["location"].split("/")[-1]

    # 2. Pay using Chapa gateway
    pay_res = client.post(
        f"/ticket/{ticket_id}/pay",
        data={"gateway": "chapa"},
        follow_redirects=False
    )
    assert pay_res.status_code == 303
    ticket = tickets_db[ticket_id]
    assert ticket.state == "PAID"
    assert getattr(ticket, "checkout_url", None) == "https://checkout.chapa.co/test-checkout"


def test_pay_ticket_with_chapa_logged_in_user(monkeypatch):
    from src.app import tickets_db

    captured_payload = {}

    class MockResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        text = '{"status":"success","message":"Hosted Link","data":{"checkout_url":"https://checkout.chapa.co/user-checkout"}}'

        def json(self):
            import json
            return json.loads(self.text)

    def mock_post(url, json=None, headers=None, timeout=None):
        captured_payload["json"] = json
        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)

    user_client = TestClient(app)
    # Register and log in
    user_client.post(
        "/register",
        data={"name": "Almaz Ayana", "email": "almaz@example.com", "password": "securepassword456"},
        follow_redirects=False
    )

    # Book ticket
    book_res = user_client.post(
        "/book",
        data={
            "passenger_name": "Almaz Ayana",
            "passenger_age": 28,
            "route_id": "R-101",
        },
        follow_redirects=False
    )
    ticket_id = book_res.headers["location"].split("/")[-1]

    # Pay with Chapa
    pay_res = user_client.post(
        f"/ticket/{ticket_id}/pay",
        data={"gateway": "chapa"},
        follow_redirects=False
    )
    assert pay_res.status_code == 303
    assert captured_payload["json"]["email"] == "almaz@example.com"
    assert captured_payload["json"]["first_name"] == "Almaz"
    assert captured_payload["json"]["last_name"] == "Ayana"
    assert tickets_db[ticket_id].state == "PAID"


def test_pay_ticket_with_telebirr_gateway():
    from src.app import tickets_db

    book_res = client.post(
        "/book",
        data={
            "passenger_name": "Telebirr User",
            "passenger_age": 24,
            "route_id": "R-202",
        },
        follow_redirects=False
    )
    assert book_res.status_code == 303
    ticket_id = book_res.headers["location"].split("/")[-1]

    pay_res = client.post(
        f"/ticket/{ticket_id}/pay",
        data={"gateway": "telebirr"},
        follow_redirects=False
    )
    assert pay_res.status_code == 303
    assert tickets_db[ticket_id].state == "PAID"

