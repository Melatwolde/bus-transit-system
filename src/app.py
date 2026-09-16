from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
import time
import uuid
import hmac
import hashlib

from src.fare import calculate_base_fare
from src.discount import calculate_discount_rate, is_peak_hour
from src.fleet import BusRoute
from src import fleet_db
from src.ticket import Ticket, PaymentGatewayInterface, ChapaTestPaymentGateway, TicketState
from src import database

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dispatch-iq-auth-secret-key-2026")


database.init_database()

templates = Jinja2Templates(directory="templates")

# Initial data store
routes_db = {
    "R-101": BusRoute("R-101", "Megenagna", "Kara", capacity=5),
    "R-202": BusRoute("R-202", "Ayertena", "Menelik II", capacity=20),
    "R-303": BusRoute("R-303", "Merkato", "Saris", capacity=30),
    "R-404": BusRoute("R-404", "Megenagna", "Legehar", capacity=18),
    "R-505": BusRoute("R-505", "Tor Hailoch", "Bole Sarbet", capacity=22),
    "R-606": BusRoute("R-606", "Kotebe", "Merkato", capacity=25),
    "R-707": BusRoute("R-707", "Megenagna", "4 Kilo", capacity=15),
    "R-808": BusRoute("R-808", "Tor Hailoch", "Ayertena", capacity=18),
    "R-909": BusRoute("R-909", "Megenagna", "Bole Airport", capacity=40),
}

# Ensure fleet DB is populated with initial in-memory routes
fleet_db.ensure_routes_populated(routes_db)

class DefaultPaymentGateway(PaymentGatewayInterface):
    def charge(self, amount: float) -> bool:
        return True

def get_current_user(request: Request):
    email = request.session.get("user_email")
    if email:
        return database.get_user_by_email(email)
    return None


def _create_auth_token(user_id: int, is_student: bool = False, is_frequent: bool = False) -> str:
    """Create a simple HMAC-signed session token containing minimal user flags."""
    secret = "dispatch-iq-auth-secret-key-2026"
    payload = f"{user_id}:{int(bool(is_student))}:{int(bool(is_frequent))}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

@app.get("/", response_class=HTMLResponse)
def get_home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="landing.html", context={
        "routes": routes_db.values(),
        "user": user
    })

@app.get("/routes", response_class=HTMLResponse)
def get_routes(request: Request):
    user = get_current_user(request)
    addis_ababa_now = datetime.now(ZoneInfo("Africa/Addis_Ababa"))
    current_status = "Peak service" if is_peak_hour(addis_ababa_now.time()) else "Off-peak service"
    frequencies = ["Every 10 minutes", "Every 15 minutes", "Every 20 minutes", "Every 12 minutes"]
    # Build rows from the authoritative routes_db so each row has a route_id
    route_rows = []
    i = 0
    for r_id, r in routes_db.items():
        route_rows.append({
            "route_id": r_id,
            "route": f"{r.origin} to {r.destination}",
            "frequency": frequencies[i % len(frequencies)],
            "window": "01:00 PM - 03:00 PM / 05:00 PM - 07:00 PM LT",
            "status": current_status,
        })
        i += 1

    return templates.TemplateResponse("routes.html", {
        "request": request,
        "routes": route_rows,
        "user": user,
        "current_status": current_status,
        "local_time": addis_ababa_now.strftime("%H:%M"),
        "timezone": "Africa/Addis_Ababa",
    })

@app.post("/book", response_class=HTMLResponse)
def create_booking(
    request: Request,
    passenger_name: str = Form(...),
    passenger_age: int = Form(...),
    route_id: str = Form(...),
    is_peak: bool = Form(False),
    is_frequent: bool = Form(False),
    is_holiday: bool = Form(False)
):
    user = get_current_user(request)
    try:
        base_fare = calculate_base_fare(passenger_age)
    except ValueError as e:
        return templates.TemplateResponse(request=request, name="landing.html", context={
            "routes": routes_db.values(),
            "user": user,
            "error_msg": str(e)
        })

    route = routes_db.get(route_id)
    # Prefer DB-backed reservation to ensure atomicity across processes
    reserved = fleet_db.reserve_seat(route_id)
    if not route or not reserved:
        return templates.TemplateResponse(request=request, name="landing.html", context={
            "routes": routes_db.values(),
            "user": user,
            "error_msg": "Selected route is at full capacity"
        })

    discount = calculate_discount_rate(is_peak, is_frequent, is_holiday)
    final_fare = round(base_fare * (1.0 - (discount / 100.0)), 2)

    ticket = Ticket(passenger_name, final_fare, route_id)
    
    user_email = user.get("email") if user else None
    database.save_ticket(ticket, user_email)

    if not user:
        guest_tickets = request.session.get("guest_tickets", [])
        guest_tickets.append(ticket.ticket_id)
        request.session["guest_tickets"] = guest_tickets

    return RedirectResponse(url=f"/ticket/{ticket.ticket_id}", status_code=303)


@app.post("/ticket/{ticket_id}/cancel")
def cancel_ticket(request: Request, ticket_id: str):
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Attempt to cancel ticket; if successful, release a seat on the route
    success = ticket.cancel()
    if success:
        # release seat in fleet DB (best-effort)
        try:
            fleet_db.release_seat(ticket.route_id)
        except Exception:
            pass
        database.save_ticket(ticket)
        return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)

    # If cancel failed, show ticket with error
    database.save_ticket(ticket)
    return templates.TemplateResponse(request=request, name="ticket.html", context={
        "ticket": ticket,
        "user": get_current_user(request),
        "error_msg": "Unable to cancel ticket"
    })

@app.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def get_ticket(request: Request, ticket_id: str):
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="ticket.html", context={
        "ticket": ticket,
        "user": user
    })

@app.post("/ticket/{ticket_id}/pay")
def pay_ticket(request: Request, ticket_id: str, gateway: str = Form("telebirr")):
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    selected_gateway = gateway.strip().lower() if gateway else "telebirr"
    if selected_gateway == "chapa":
        user = get_current_user(request)
        names = ticket.passenger_name.strip().split(" ", 1)
        first_name = names[0] if names else "Passenger"
        last_name = names[1] if len(names) > 1 else "Customer"
        safe_name = first_name.lower().replace(" ", "")
        email = user.get("email") if user and user.get("email") else "test@chapa.co"
        tx_ref = f"tx-{ticket.ticket_id}-{uuid.uuid4().hex[:8]}"
        return_url = str(request.url_for("payment_return", ticket_id=ticket.ticket_id))
        chapa_gateway = ChapaTestPaymentGateway(
            email=email,
            first_name=first_name,
            last_name=last_name,
            tx_ref=tx_ref,
        return_url=return_url,
        )
        
        success = ticket.pay(chapa_gateway)
        database.save_ticket(ticket)
        
        # Print debug info to your terminal to see why Chapa failed
        print("Chapa Success:", success)
        print("Chapa Last Status Code:", chapa_gateway.last_status_code)
        print("Chapa Last Response:", chapa_gateway.last_response)
        print("Chapa Last Error:", chapa_gateway.last_error)
        print("Chapa Secret Key Loaded?:", bool(chapa_gateway.secret_key))

        if getattr(chapa_gateway, "checkout_url", None):
            return RedirectResponse(url=chapa_gateway.checkout_url, status_code=303)
    else:
        ticket.pay(DefaultPaymentGateway())
        database.save_ticket(ticket)

    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)
@app.post("/ticket/{ticket_id}/scan")
def scan_ticket(ticket_id: str):
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.validate_boarding()
    database.save_ticket(ticket)
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={
        "mode": "login",
        "user": None
    })

@app.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    account = database.authenticate_user(email, password)
    if not account:
        return templates.TemplateResponse(request=request, name="login.html", context={
            "mode": "login",
            "error_msg": "Invalid email or password",
            "user": None
        })
    request.session["user_email"] = email
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={
        "mode": "register",
        "user": None
    })

@app.post("/register", response_class=HTMLResponse)
def post_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...)
):
    account = database.create_user(email, password, name)
    if not account:
        return templates.TemplateResponse(request=request, name="login.html", context={
            "mode": "register",
            "error_msg": "Email is already registered",
            "user": None
        })
    # Initialize session state immediately after registration
    request.session["user_email"] = email
    request.session["user_id"] = account.get("id")
    # Default flags for new users; these can be changed later by profile actions
    request.session["is_student"] = False
    request.session["is_frequent_rider"] = False
    # Create a signed session token and persist it in the session cookie
    request.session["auth_token"] = _create_auth_token(request.session["user_id"], False, False)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/routes/{route_id}/book")
def route_book(request: Request, route_id: str):
    """Session-aware booking entry point.

    Redirects authenticated users to the authenticated booking flow and
    falls back to the guest flow for anonymous users.
    """
    user = get_current_user(request)
    # preserve route context for downstream flows
    if user:
        return RedirectResponse(url=f"/bookings/create?route_id={route_id}", status_code=303)
    else:
        return RedirectResponse(url=f"/bookings/guest?route_id={route_id}", status_code=303)

@app.api_route("/logout", methods=["GET", "POST"])
def logout(request: Request):
    request.session.pop("user_email", None)
    return RedirectResponse(url="/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    user_tickets = database.get_user_tickets(user["email"])
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "tickets": user_tickets
    })


@app.get("/conductor", response_class=HTMLResponse)
def get_conductor(request: Request):
    user = get_current_user(request)
    # minimal access control could be added here
    routes = fleet_db.get_all_routes()
    return templates.TemplateResponse(request=request, name="conductor.html", context={
        "routes": routes,
        "user": user
    })
@app.get("/payment/return/{ticket_id}")
def payment_return(request: Request, ticket_id: str, tx_ref: Optional[str] = None):
    ticket = database.get_ticket(ticket_id)
    if ticket and ticket.state == TicketState.ISSUED.value:
       
        ticket.state = TicketState.PAID.value
        ticket.generate_token()
        database.save_ticket(ticket)
    
    
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)