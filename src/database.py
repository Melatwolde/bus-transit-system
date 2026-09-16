import sqlite3
from pathlib import Path
import hashlib
import hmac
import secrets

import os

DB_PATH_ENV = os.getenv("DB_PATH")
if DB_PATH_ENV:
    DATABASE_PATH = DB_PATH_ENV
else:
    DATABASE_PATH = Path(__file__).resolve().parent.parent / "bus_transit.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            passenger_name TEXT NOT NULL,
            fare REAL NOT NULL,
            route_id TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            verification_hash TEXT,
            qr_code TEXT,
            user_email TEXT,
            FOREIGN KEY(user_email) REFERENCES users(email)
        )
    """)

    connection.commit()
    connection.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000
    )

    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, password_hash_hex = stored_hash.split(":", 1)

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(password_hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100_000
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str, name: str):
    connection = get_connection()

    password_hash = hash_password(password)

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash, name)
            VALUES (?, ?, ?)
            """,
            (email, password_hash, name)
        )

        connection.commit()

        return {
            "id": cursor.lastrowid,
            "email": email,
            "name": name,
            "tickets": []
        }

    except sqlite3.IntegrityError:
        return None

    finally:
        connection.close()


def get_user_by_email(email: str):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT id, email, password_hash, name
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)

    if user is None:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "tickets": []
    }

from src.ticket import Ticket, TicketState

def save_ticket(ticket: Ticket, user_email: str = None):
    connection = get_connection()
    try:
        if user_email is None:
            existing = connection.execute("SELECT user_email FROM tickets WHERE ticket_id = ?", (ticket.ticket_id,)).fetchone()
            if existing:
                user_email = existing["user_email"]
            
        connection.execute("""
            INSERT OR REPLACE INTO tickets (ticket_id, passenger_name, fare, route_id, state, created_at, expires_at, verification_hash, qr_code, user_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket.ticket_id, ticket.passenger_name, ticket.fare, ticket.route_id, ticket.state, ticket.created_at, ticket.expires_at, ticket.verification_hash, ticket.qr_code, user_email))
        connection.commit()
    finally:
        connection.close()

def get_ticket(ticket_id: str) -> 'Ticket | None':
    connection = get_connection()
    row = connection.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    connection.close()
    if not row:
        return None
    ticket = Ticket(
        passenger_name=row["passenger_name"],
        fare=row["fare"],
        route_id=row["route_id"],
        ticket_id=row["ticket_id"],
        expires_at=row["expires_at"],
        created_at=row["created_at"]
    )
    ticket.state = row["state"]
    ticket.verification_hash = row["verification_hash"]
    ticket.qr_code = row["qr_code"]
    return ticket

def get_user_tickets(email: str):
    connection = get_connection()
    rows = connection.execute("SELECT * FROM tickets WHERE user_email = ? ORDER BY created_at DESC", (email,)).fetchall()
    connection.close()
    tickets = []
    for row in rows:
        ticket = Ticket(
            passenger_name=row["passenger_name"],
            fare=row["fare"],
            route_id=row["route_id"],
            ticket_id=row["ticket_id"],
            expires_at=row["expires_at"],
            created_at=row["created_at"]
        )
        ticket.state = row["state"]
        ticket.verification_hash = row["verification_hash"]
        ticket.qr_code = row["qr_code"]
        tickets.append(ticket)
    return tickets
