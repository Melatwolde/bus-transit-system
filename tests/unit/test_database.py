import pytest
import sqlite3
from src import database
from src.ticket import Ticket, TicketState

def test_database_initialization():
    database.init_database()
    conn = database.get_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t["name"] for t in tables]
    assert "users" in table_names
    assert "tickets" in table_names
    conn.close()

def test_user_operations():
    # create user
    user1 = database.create_user("dbtest@example.com", "pass123", "DB Test")
    assert user1 is not None
    assert user1["email"] == "dbtest@example.com"
    
    # retrieve user
    retrieved = database.get_user_by_email("dbtest@example.com")
    assert retrieved is not None
    assert retrieved["name"] == "DB Test"
    
    # authenticate user
    auth = database.authenticate_user("dbtest@example.com", "pass123")
    assert auth is not None
    assert auth["email"] == "dbtest@example.com"
    
    # invalid login
    invalid_auth = database.authenticate_user("dbtest@example.com", "wrongpass")
    assert invalid_auth is None
    
    # duplicate email
    duplicate_user = database.create_user("dbtest@example.com", "pass123", "Duplicate")
    assert duplicate_user is None
    
    # retrieve non-existent user
    non_existent = database.get_user_by_email("nonexistent@example.com")
    assert non_existent is None
    
    # auth non-existent user
    invalid_auth_2 = database.authenticate_user("nonexistent@example.com", "pass123")
    assert invalid_auth_2 is None

def test_ticket_operations():
    user = database.create_user("ticketuser@example.com", "pass123", "Ticket User")
    
    ticket = Ticket("John Doe", 100.0, "R-101")
    database.save_ticket(ticket, "ticketuser@example.com")
    
    retrieved = database.get_ticket(ticket.ticket_id)
    assert retrieved is not None
    assert retrieved.passenger_name == "John Doe"
    assert retrieved.fare == 100.0
    assert retrieved.state == TicketState.ISSUED.value
    
    # update state
    retrieved.state = TicketState.PAID.value
    retrieved.generate_token()
    database.save_ticket(retrieved)
    
    updated = database.get_ticket(ticket.ticket_id)
    assert updated.state == TicketState.PAID.value
    assert updated.verification_hash is not None
    
    # test get_user_tickets
    tickets = database.get_user_tickets("ticketuser@example.com")
    assert len(tickets) >= 1
    assert any(t.ticket_id == ticket.ticket_id for t in tickets)
    
    # missing ticket
    assert database.get_ticket("missing-id") is None
