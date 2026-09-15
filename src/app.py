from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.fare import calculate_base_fare
from src.discount import calculate_discount_rate, is_peak_hour
from src.fleet import BusRoute
from src.ticket import Ticket, PaymentGatewayInterface

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dispatch-iq-auth-secret-key-2026")

templates = Jinja2Templates(directory="templates")

# In-memory mock user dictionary storing {"email": {"password": "...", "name": "...", "tickets": [...]}}
users_db = {}

# Initial data store
routes_db = {
    "R-101": BusRoute("R-101", "Megenagna", "Kara", capacity=5),
    "R-202": BusRoute("R-202", "Ayertena", "Menelik II Square"),
    "R-303": BusRoute("R-303", "Merkato", "Saris", capacity=30),
    "R-404": BusRoute("R-404", "Megenagna", "Legehar"),
    "R-505": BusRoute("R-505", "Tor Hailoch", "BoleSarbet"),
    "R-606": BusRoute("R-606", "Kotebe", "Merkato"),
    "R-707": BusRoute("R-707", "Megenagna", "4 Kilo"),
    "R-808": BusRoute("R-808", "Tor Hailoch", "Ayertena"),
    "45": BusRoute("45", "Megenagna", "Bole Airport", capacity=40)
}
tickets_db = {}

class DefaultPaymentGateway(PaymentGatewayInterface):
    def charge(self, amount: float) -> bool:
        return True

def get_current_user(request: Request):
    email = request.session.get("user_email")
    if email and email in users_db:
        return users_db[email]
    return None

@app.get("/", response_class=HTMLResponse)
def get_home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "routes": routes_db.values(),
        "user": user
    })

@app.get("/routes", response_class=HTMLResponse)
def get_routes(request: Request):
    user = get_current_user(request)
    addis_ababa_now = datetime.now(ZoneInfo("Africa/Addis_Ababa"))
    current_status = "Peak service" if is_peak_hour(addis_ababa_now.time()) else "Off-peak service"
    frequencies = ["Every 10 minutes", "Every 15 minutes", "Every 20 minutes"]
    schedules = [
        {
            "route": route,
            "frequency": frequencies[index % len(frequencies)],
            "peak": "07:00-09:00 AM LT / 05:00-07:00 PM LT",
            "status": current_status,
        }
        for index, route in enumerate(routes_db.values())
    ]
    return templates.TemplateResponse("routes.html", {
        "request": request,
        "schedules": schedules,
        "user": user,
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
        return templates.TemplateResponse("index.html", {
            "request": request,
            "routes": routes_db.values(),
            "user": user,
            "error_msg": str(e)
        })

    route = routes_db.get(route_id)
    if not route or not route.reserve_seat():
        return templates.TemplateResponse("index.html", {
            "request": request,
            "routes": routes_db.values(),
            "user": user,
            "error_msg": "Selected route is at full capacity"
        })

    discount = calculate_discount_rate(is_peak, is_frequent, is_holiday)
    final_fare = round(base_fare * (1.0 - (discount / 100.0)), 2)

    ticket = Ticket(passenger_name, final_fare, route_id)
    tickets_db[ticket.ticket_id] = ticket

    if user:
        user["tickets"].append(ticket.ticket_id)
    else:
        guest_tickets = request.session.get("guest_tickets", [])
        guest_tickets.append(ticket.ticket_id)
        request.session["guest_tickets"] = guest_tickets

    return RedirectResponse(url=f"/ticket/{ticket.ticket_id}", status_code=303)

@app.get("/ticket/{ticket_id}", response_class=HTMLResponse)
def get_ticket(request: Request, ticket_id: str):
    ticket = tickets_db.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    user = get_current_user(request)
    return templates.TemplateResponse("ticket.html", {
        "request": request,
        "ticket": ticket,
        "user": user
    })

@app.post("/ticket/{ticket_id}/pay")
def pay_ticket(ticket_id: str, gateway: str = Form("telebirr")):
    ticket = tickets_db.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.pay(DefaultPaymentGateway())
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)

@app.post("/ticket/{ticket_id}/scan")
def scan_ticket(ticket_id: str):
    ticket = tickets_db.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.validate_boarding()
    return RedirectResponse(url=f"/ticket/{ticket_id}", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "mode": "login",
        "user": None
    })

@app.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    account = users_db.get(email)
    if not account or account["password"] != password:
        return templates.TemplateResponse("login.html", {
            "request": request,
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
    return templates.TemplateResponse("login.html", {
        "request": request,
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
    if email in users_db:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "mode": "register",
            "error_msg": "Email is already registered",
            "user": None
        })
    
    users_db[email] = {
        "email": email,
        "password": password,
        "name": name,
        "tickets": []
    }
    request.session["user_email"] = email
    return RedirectResponse(url="/dashboard", status_code=303)

@app.api_route("/logout", methods=["GET", "POST"])
def logout(request: Request):
    request.session.pop("user_email", None)
    return RedirectResponse(url="/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    user_tickets = [tickets_db[tid] for tid in user.get("tickets", []) if tid in tickets_db]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "tickets": user_tickets
    })