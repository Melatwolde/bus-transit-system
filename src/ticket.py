import os
import uuid
import hashlib
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Union, Dict, Any
import requests
from dotenv import load_dotenv

# Ensure root .env is loaded if available
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


class IllegalStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted on a ticket."""
    pass


class TicketState(str, Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    VALIDATED = "VALIDATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    def __str__(self) -> str:
        return self.value


class PaymentGatewayInterface:
    def charge(self, amount: float) -> bool:
        raise NotImplementedError("Real gateway unreachable in unit test")


class DefaultPaymentGateway(PaymentGatewayInterface):
    def charge(self, amount: float) -> bool:
        return True


class ChapaTestPaymentGateway(PaymentGatewayInterface):
    INITIALIZE_URL = "https://api.chapa.co/v1/transaction/initialize"

    def __init__(
        self,
        secret_key: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        tx_ref: Optional[str] = None,
        currency: str = "ETB",
        callback_url: Optional[str] = None,
        return_url: Optional[str] = None,
        customization_title: str = "Bus Ticket Payment",
        customization_description: str = "Bus Transit Ticket Payment",
    ):
        self.secret_key = secret_key or os.getenv("CHAPA_SECRET_KEY")
        self.email = email or "passenger@example.com"
        self.first_name = first_name or "Passenger"
        self.last_name = last_name or "Customer"
        self.phone_number = phone_number
        self.tx_ref = tx_ref
        self.currency = currency
        self.callback_url = callback_url
        self.return_url = return_url
        self.customization_title = customization_title
        self.customization_description = customization_description

        self.checkout_url: Optional[str] = None
        self.last_response: Optional[Dict[str, Any]] = None
        self.last_status_code: Optional[int] = None
        self.last_error: Optional[str] = None

    def charge(self, amount: float, **kwargs) -> bool:
        if not self.secret_key:
            self.last_error = "CHAPA_SECRET_KEY is not configured"
            return False

        email = kwargs.get("email", self.email)
        first_name = kwargs.get("first_name", self.first_name)
        last_name = kwargs.get("last_name", self.last_name)
        phone_number = kwargs.get("phone_number", self.phone_number)
        currency = kwargs.get("currency", self.currency)
        tx_ref = kwargs.get("tx_ref", self.tx_ref) or f"chapa-{uuid.uuid4().hex[:12]}"
        callback_url = kwargs.get("callback_url", self.callback_url)
        return_url = kwargs.get("return_url", self.return_url)
        title = kwargs.get("title", self.customization_title)
        description = kwargs.get("description", self.customization_description)

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "amount": str(amount),
            "currency": currency,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": tx_ref,
        }
        if phone_number:
            payload["phone_number"] = phone_number
        if callback_url:
            payload["callback_url"] = callback_url
        if return_url:
            payload["return_url"] = return_url
        if title:
            payload["customization[title]"] = title
        if description:
            payload["customization[description]"] = description

        try:
            response = requests.post(
                self.INITIALIZE_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )
            self.last_status_code = response.status_code
            try:
                data = response.json()
            except Exception:
                data = {"message": response.text, "status": "failed"}
            self.last_response = data

            if response.status_code == 200 and data.get("status") == "success":
                data_obj = data.get("data")
                if isinstance(data_obj, dict):
                    self.checkout_url = data_obj.get("checkout_url")
                return True
            return False
        except Exception as e:
            self.last_error = str(e)
            return False


class Ticket:
    VALID_STATES = {state.value for state in TicketState}

    def __init__(
        self,
        passenger_name: str,
        fare: float,
        route_id: str,
        ticket_id: Optional[str] = None,
        validity_seconds: int = 86400,
        expires_at: Optional[float] = None,
        created_at: Optional[float] = None
    ):
        self.ticket_id = ticket_id or str(uuid.uuid4())[:8]
        self.passenger_name = passenger_name
        self.fare = fare
        self.route_id = route_id
        self.state = TicketState.ISSUED.value

        self.created_at = created_at if created_at is not None else time.time()
        self.expires_at = (
            expires_at
            if expires_at is not None
            else self.created_at + validity_seconds
        )

        self.verification_hash: Optional[str] = None
        self.qr_code: Optional[str] = None

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Check if ticket validity window has elapsed."""
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at

    def check_expiration(self, current_time: Optional[float] = None) -> bool:
        """Transition ticket to EXPIRED if timestamp has elapsed and state is active."""
        if self.is_expired(current_time):
            if self.state in {TicketState.ISSUED.value, TicketState.PAID.value}:
                self.state = TicketState.EXPIRED.value
                return True
        return False

    def generate_token(self) -> str:
        """Generate SHA-256 verification hash and 16-char QR representation."""
        raw_token = (
            f"{self.ticket_id}:{self.passenger_name}:{self.route_id}:{int(self.expires_at)}"
        )
        self.verification_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        self.qr_code = self.verification_hash[:16]
        return self.verification_hash

    def verify_token(self, token: str, current_time: Optional[float] = None) -> bool:
        """Verify token hash against expected SHA-256 hash and expiration timestamp."""
        if not token:
            return False

        if self.is_expired(current_time):
            self.check_expiration(current_time)
            return False

        if self.state in {TicketState.CANCELLED.value, TicketState.EXPIRED.value}:
            return False

        # Compute expected hash using ticket parameters and expiration
        raw_token = (
            f"{self.ticket_id}:{self.passenger_name}:{self.route_id}:{int(self.expires_at)}"
        )
        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Support either full 64-char SHA-256 digest or 16-char QR slice
        is_hash_valid = (
            token == expected_hash or
            token == expected_hash[:16] or
            (self.verification_hash and token == self.verification_hash) or
            (self.qr_code and token == self.qr_code)
        )
        return bool(is_hash_valid)

    def pay(
        self,
        gateway: PaymentGatewayInterface,
        raise_on_error: bool = False,
        current_time: Optional[float] = None
    ) -> bool:
        """Process payment and transition from ISSUED to PAID with token generation."""
        if self.is_expired(current_time):
            self.state = TicketState.EXPIRED.value
            if raise_on_error:
                raise IllegalStateTransitionError("Cannot pay for an expired ticket")
            return False

        if self.state != TicketState.ISSUED.value:
            if raise_on_error:
                raise IllegalStateTransitionError(
                    f"Cannot pay ticket in state {self.state}. Must be in ISSUED state."
                )
            return False

        if gateway.charge(self.fare):
            self.state = TicketState.PAID.value
            self.generate_token()
            return True

        return False

    def validate_boarding(
        self,
        token: Optional[str] = None,
        raise_on_error: bool = False,
        current_time: Optional[float] = None
    ) -> bool:
        """Validate ticket boarding. Blocks cancelled, expired, or invalid tickets."""
        if self.is_expired(current_time):
            self.state = TicketState.EXPIRED.value
            if raise_on_error:
                raise IllegalStateTransitionError("Cannot validate an expired ticket")
            return False

        if self.state != TicketState.PAID.value:
            if raise_on_error:
                raise IllegalStateTransitionError(
                    f"Illegal transition: Cannot scan/validate ticket in state {self.state}."
                )
            return False

        if token is not None and not self.verify_token(token, current_time):
            if raise_on_error:
                raise IllegalStateTransitionError("Invalid token for boarding validation")
            return False

        self.state = TicketState.VALIDATED.value
        return True

    def cancel(self, raise_on_error: bool = False, current_time: Optional[float] = None) -> bool:
        """Cancel ticket. Blocks cancelling/refunding a validated, cancelled, or expired ticket."""
        if self.state == TicketState.VALIDATED.value:
            if raise_on_error:
                raise IllegalStateTransitionError("Illegal transition: Cannot refund a validated ticket")
            return False

        if self.state in {TicketState.CANCELLED.value, TicketState.EXPIRED.value}:
            if raise_on_error:
                raise IllegalStateTransitionError(
                    f"Illegal transition: Ticket is already {self.state}"
                )
            return False

        if self.is_expired(current_time):
            self.state = TicketState.EXPIRED.value
            if raise_on_error:
                raise IllegalStateTransitionError("Illegal transition: Cannot cancel an expired ticket")
            return False

        self.state = TicketState.CANCELLED.value
        return True

    def refund(self, raise_on_error: bool = False, current_time: Optional[float] = None) -> bool:
        """Refund a paid ticket. Transition guard blocks refunding a validated or expired ticket."""
        if self.state == TicketState.VALIDATED.value:
            if raise_on_error:
                raise IllegalStateTransitionError("Illegal transition: Cannot refund a validated ticket")
            return False

        if self.state != TicketState.PAID.value:
            if raise_on_error:
                raise IllegalStateTransitionError(
                    f"Illegal transition: Cannot refund ticket in state {self.state}. Must be PAID."
                )
            return False

        if self.is_expired(current_time):
            self.state = TicketState.EXPIRED.value
            if raise_on_error:
                raise IllegalStateTransitionError("Illegal transition: Cannot refund an expired ticket")
            return False

        self.state = TicketState.CANCELLED.value
        return True

    def expire(self, raise_on_error: bool = False) -> bool:
        """Manually or rule-based transition of ticket to EXPIRED."""
        if self.state in {TicketState.ISSUED.value, TicketState.PAID.value}:
            self.state = TicketState.EXPIRED.value
            return True

        if raise_on_error:
            raise IllegalStateTransitionError(
                f"Illegal transition: Cannot expire ticket in state {self.state}"
            )
        return False
