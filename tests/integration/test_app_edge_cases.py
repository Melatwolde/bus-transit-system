from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_login_register_redirects_if_logged_in():
    # Register a user and log in to get a session
    client.post("/register", data={"name": "Edge", "email": "edge@example.com", "password": "pass"})
    
    # Try to access login page
    res_login = client.get("/login", follow_redirects=False)
    assert res_login.status_code in [302, 303, 307]
    
    # Try to access register page
    res_register = client.get("/register", follow_redirects=False)
    assert res_register.status_code in [302, 303, 307]
    
    # Log out
    client.get("/logout")

def test_login_invalid_credentials():
    res = client.post("/login", data={"email": "wrong@example.com", "password": "wrong"})
    assert res.status_code == 200
    assert "Invalid email or password" in res.text

def test_register_duplicate_email():
    client.post("/register", data={"name": "Dup", "email": "dup@example.com", "password": "pass"})
    res = client.post("/register", data={"name": "Dup2", "email": "dup@example.com", "password": "pass2"})
    assert res.status_code == 200
    assert "Email is already registered" in res.text

def test_dashboard_redirects_when_not_logged_in():
    unauth_client = TestClient(app)
    res = unauth_client.get("/dashboard", follow_redirects=False)
    assert res.status_code in [302, 303, 307]
