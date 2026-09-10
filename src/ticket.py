import uuid
import hashlib

class PaymentGatewayInterface:
    def charge(self, amount: float) -> bool:
        raise NotImplementedError("Real gateway unreachable in unit test")

class Ticket:
    VALID_STATES = {"ISSUED", "PAID", "VALIDATED", "CANCELLED"}

    def __init__(self, passenger_name: str, fare: float, route_id: str):
        self.ticket_id = str(uuid.uuid4())[:8]
        self.passenger_name = passenger_name
        self.fare = fare
        self.route_id = route_id
        self.state = "ISSUED"
        self.qr_code = None

    def pay(self, gateway: PaymentGatewayInterface) -> bool:
        if self.state != "ISSUED":
            return False
        if gateway.charge(self.fare):
            self.state = "PAID"
            raw_token = f"{self.ticket_id}:{self.passenger_name}:{self.route_id}"
            self.qr_code = hashlib.sha256(raw_token.encode()).hexdigest()[:16]
            return True
        return False

    def validate_boarding(self) -> bool:
        if self.state == "PAID":
            self.state = "VALIDATED"
            return True
        return False

    def cancel(self) -> bool:
        if self.state in {"ISSUED", "PAID"}:
            self.state = "CANCELLED"
            return True
        return False
