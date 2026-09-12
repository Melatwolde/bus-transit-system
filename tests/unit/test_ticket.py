import time
import pytest
import hashlib
from src.ticket import (
    Ticket,
    TicketState,
    IllegalStateTransitionError,
    PaymentGatewayInterface,
)


class MockSuccessGateway(PaymentGatewayInterface):
    def charge(self, amount: float) -> bool:
        return True


class MockFailGateway(PaymentGatewayInterface):
    def charge(self, amount: float) -> bool:
        return False


def test_payment_gateway_interface_raises_not_implemented():
    gateway = PaymentGatewayInterface()
    with pytest.raises(NotImplementedError):
        gateway.charge(50.0)


def test_ticket_states_enumeration_and_valid_states():
    expected_states = {"ISSUED", "PAID", "VALIDATED", "CANCELLED", "EXPIRED"}
    assert {s.value for s in TicketState} == expected_states
    assert Ticket.VALID_STATES == expected_states
    assert str(TicketState.ISSUED) == "ISSUED"


def test_ticket_initialization():
    now = time.time()
    ticket = Ticket(
        passenger_name="Abebe Bikila",
        fare=45.0,
        route_id="R-101",
        ticket_id="TICK-1234",
        validity_seconds=3600,
        created_at=now,
    )

    assert ticket.ticket_id == "TICK-1234"
    assert ticket.passenger_name == "Abebe Bikila"
    assert ticket.fare == 45.0
    assert ticket.route_id == "R-101"
    assert ticket.state == TicketState.ISSUED.value
    assert ticket.created_at == now
    assert ticket.expires_at == now + 3600
    assert ticket.qr_code is None
    assert ticket.verification_hash is None
    assert not ticket.is_expired(current_time=now + 100)


def test_payment_success_and_token_generation():
    now = time.time()
    ticket = Ticket("Derartu Tulu", 30.0, "R-202", ticket_id="TICK-9999", created_at=now, validity_seconds=3600)
    gateway = MockSuccessGateway()

    result = ticket.pay(gateway, current_time=now + 10)
    assert result is True
    assert ticket.state == TicketState.PAID.value
    assert ticket.verification_hash is not None
    assert len(ticket.verification_hash) == 64
    assert ticket.qr_code is not None
    assert len(ticket.qr_code) == 16
    assert ticket.qr_code == ticket.verification_hash[:16]

    # Verify SHA-256 formula with expiration timestamp
    raw_expected = f"{ticket.ticket_id}:{ticket.passenger_name}:{ticket.route_id}:{int(ticket.expires_at)}"
    expected_sha = hashlib.sha256(raw_expected.encode("utf-8")).hexdigest()
    assert ticket.verification_hash == expected_sha


def test_payment_failure_gateway_declined():
    ticket = Ticket("Haile G.", 25.0, "R-101")
    gateway = MockFailGateway()

    result = ticket.pay(gateway)
    assert result is False
    assert ticket.state == TicketState.ISSUED.value
    assert ticket.qr_code is None


def test_payment_illegal_transitions_and_guards():
    ticket = Ticket("Kenenisa B.", 50.0, "R-101")
    gateway = MockSuccessGateway()

    # 1. Pay once -> PAID
    assert ticket.pay(gateway) is True

    # 2. Paying again when already PAID should fail
    assert ticket.pay(gateway) is False
    with pytest.raises(IllegalStateTransitionError, match="Must be in ISSUED state"):
        ticket.pay(gateway, raise_on_error=True)

    # 3. Paying after VALIDATED should fail
    assert ticket.validate_boarding() is True
    assert ticket.pay(gateway) is False
    with pytest.raises(IllegalStateTransitionError):
        ticket.pay(gateway, raise_on_error=True)


def test_payment_blocked_when_expired():
    now = time.time()
    ticket = Ticket("Tirunesh D.", 35.0, "R-101", created_at=now, validity_seconds=100)
    gateway = MockSuccessGateway()

    future_time = now + 500  # past expiration
    assert ticket.pay(gateway, current_time=future_time) is False
    assert ticket.state == TicketState.EXPIRED.value

    # Test raise_on_error for expired payment
    ticket2 = Ticket("Tirunesh D.", 35.0, "R-101", created_at=now, validity_seconds=100)
    with pytest.raises(IllegalStateTransitionError, match="Cannot pay for an expired ticket"):
        ticket2.pay(gateway, raise_on_error=True, current_time=future_time)


def test_boarding_validation_success():
    ticket = Ticket("Sileshi S.", 20.0, "R-101")
    ticket.pay(MockSuccessGateway())

    # Validating boarding transitions PAID -> VALIDATED
    assert ticket.validate_boarding() is True
    assert ticket.state == TicketState.VALIDATED.value


def test_boarding_validation_with_token_verification():
    now = time.time()
    ticket = Ticket("Meseret D.", 40.0, "R-202", created_at=now, validity_seconds=3600)
    ticket.pay(MockSuccessGateway(), current_time=now)

    full_token = ticket.verification_hash
    qr_token = ticket.qr_code
    invalid_token = "invalid_tampered_token_hash"

    # Token verification method tests
    assert ticket.verify_token(full_token, current_time=now + 50) is True
    assert ticket.verify_token(qr_token, current_time=now + 50) is True
    assert ticket.verify_token(invalid_token, current_time=now + 50) is False
    assert ticket.verify_token("", current_time=now + 50) is False
    assert ticket.verify_token(None, current_time=now + 50) is False

    # Token verification fails when expired
    assert ticket.verify_token(full_token, current_time=now + 4000) is False
    assert ticket.state == TicketState.EXPIRED.value

    # Reset ticket and validate boarding with token
    ticket2 = Ticket("Meseret D.", 40.0, "R-202", created_at=now, validity_seconds=3600)
    ticket2.pay(MockSuccessGateway(), current_time=now)

    # Valid token boarding
    assert ticket2.validate_boarding(token=ticket2.qr_code, current_time=now + 10) is True
    assert ticket2.state == TicketState.VALIDATED.value

    # Invalid token boarding raises error or returns False
    ticket3 = Ticket("Meseret D.", 40.0, "R-202", created_at=now, validity_seconds=3600)
    ticket3.pay(MockSuccessGateway(), current_time=now)
    assert ticket3.validate_boarding(token="tampered_hash", current_time=now + 10) is False
    with pytest.raises(IllegalStateTransitionError, match="Invalid token"):
        ticket3.validate_boarding(token="tampered_hash", raise_on_error=True, current_time=now + 10)


def test_transition_guard_blocks_scanning_cancelled_ticket():
    ticket = Ticket("Gudaf T.", 50.0, "R-101")
    ticket.pay(MockSuccessGateway())
    assert ticket.cancel() is True
    assert ticket.state == TicketState.CANCELLED.value

    # Transition guard: Scanning a cancelled ticket is strictly blocked!
    assert ticket.validate_boarding() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot scan/validate ticket in state CANCELLED"):
        ticket.validate_boarding(raise_on_error=True)


def test_transition_guard_blocks_scanning_unpaid_or_double_boarding():
    # 1. Unpaid (ISSUED) ticket cannot be scanned
    ticket = Ticket("Selemon B.", 25.0, "R-101")
    assert ticket.validate_boarding() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot scan/validate ticket in state ISSUED"):
        ticket.validate_boarding(raise_on_error=True)

    # 2. Double boarding: Validated ticket cannot be scanned again
    ticket.pay(MockSuccessGateway())
    assert ticket.validate_boarding() is True
    assert ticket.validate_boarding() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot scan/validate ticket in state VALIDATED"):
        ticket.validate_boarding(raise_on_error=True)


def test_transition_guard_blocks_scanning_expired_ticket():
    now = time.time()
    ticket = Ticket("Berhane A.", 25.0, "R-101", created_at=now, validity_seconds=200)
    ticket.pay(MockSuccessGateway(), current_time=now)

    # Attempt to scan after expiration timestamp
    scan_time = now + 300
    assert ticket.validate_boarding(current_time=scan_time) is False
    assert ticket.state == TicketState.EXPIRED.value

    # Raise on error
    ticket2 = Ticket("Berhane A.", 25.0, "R-101", created_at=now, validity_seconds=200)
    ticket2.pay(MockSuccessGateway(), current_time=now)
    with pytest.raises(IllegalStateTransitionError, match="Cannot validate an expired ticket"):
        ticket2.validate_boarding(raise_on_error=True, current_time=scan_time)


def test_transition_guard_blocks_refunding_validated_ticket():
    ticket = Ticket("Getnet W.", 30.0, "R-202")
    ticket.pay(MockSuccessGateway())
    ticket.validate_boarding()
    assert ticket.state == TicketState.VALIDATED.value

    # Transition guard: Refunding a validated ticket is strictly blocked!
    assert ticket.refund() is False
    assert ticket.cancel() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot refund a validated ticket"):
        ticket.refund(raise_on_error=True)
    with pytest.raises(IllegalStateTransitionError, match="Cannot refund a validated ticket"):
        ticket.cancel(raise_on_error=True)


def test_cancellation_and_refund_flows():
    # 1. Cancel ISSUED ticket
    t1 = Ticket("Fatuma R.", 20.0, "R-101")
    assert t1.cancel() is True
    assert t1.state == TicketState.CANCELLED.value
    # Cancelling again fails
    assert t1.cancel() is False
    with pytest.raises(IllegalStateTransitionError, match="already CANCELLED"):
        t1.cancel(raise_on_error=True)

    # 2. Refund PAID ticket
    t2 = Ticket("Fatuma R.", 20.0, "R-101")
    t2.pay(MockSuccessGateway())
    assert t2.refund() is True
    assert t2.state == TicketState.CANCELLED.value

    # Refunding when already CANCELLED fails
    assert t2.refund() is False
    with pytest.raises(IllegalStateTransitionError, match="Must be PAID"):
        t2.refund(raise_on_error=True)


def test_refund_and_cancellation_blocked_when_expired():
    now = time.time()
    t = Ticket("Gebrselassie", 20.0, "R-101", created_at=now, validity_seconds=50)
    t.pay(MockSuccessGateway(), current_time=now)

    later = now + 100
    assert t.refund(current_time=later) is False
    assert t.state == TicketState.EXPIRED.value

    t2 = Ticket("Gebrselassie", 20.0, "R-101", created_at=now, validity_seconds=50)
    t2.pay(MockSuccessGateway(), current_time=now)
    with pytest.raises(IllegalStateTransitionError, match="Cannot refund an expired ticket"):
        t2.refund(raise_on_error=True, current_time=later)

    t3 = Ticket("Gebrselassie", 20.0, "R-101", created_at=now, validity_seconds=50)
    assert t3.cancel(current_time=later) is False
    assert t3.state == TicketState.EXPIRED.value

    t4 = Ticket("Gebrselassie", 20.0, "R-101", created_at=now, validity_seconds=50)
    with pytest.raises(IllegalStateTransitionError, match="Cannot cancel an expired ticket"):
        t4.cancel(raise_on_error=True, current_time=later)


def test_expiration_methods():
    now = time.time()
    ticket = Ticket("Kenenisa", 15.0, "R-101", created_at=now, validity_seconds=100)

    # Not expired yet
    assert ticket.is_expired(current_time=now + 50) is False
    assert ticket.check_expiration(current_time=now + 50) is False
    assert ticket.state == TicketState.ISSUED.value

    # Expired
    assert ticket.is_expired(current_time=now + 150) is True
    assert ticket.check_expiration(current_time=now + 150) is True
    assert ticket.state == TicketState.EXPIRED.value

    # check_expiration on already expired/validated/cancelled ticket returns False
    t_validated = Ticket("Validated", 15.0, "R-101", created_at=now, validity_seconds=100)
    t_validated.pay(MockSuccessGateway(), current_time=now)
    t_validated.validate_boarding()
    assert t_validated.check_expiration(current_time=now + 200) is False

    # Explicit expire() method
    t_issued = Ticket("Abeba", 15.0, "R-101")
    assert t_issued.expire() is True
    assert t_issued.state == TicketState.EXPIRED.value

    t_paid = Ticket("Abeba", 15.0, "R-101")
    t_paid.pay(MockSuccessGateway())
    assert t_paid.expire() is True
    assert t_paid.state == TicketState.EXPIRED.value

    # Cannot expire VALIDATED or CANCELLED tickets
    t_val = Ticket("Abeba", 15.0, "R-101")
    t_val.pay(MockSuccessGateway())
    t_val.validate_boarding()
    assert t_val.expire() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot expire ticket in state VALIDATED"):
        t_val.expire(raise_on_error=True)

    t_can = Ticket("Abeba", 15.0, "R-101")
    t_can.cancel()
    assert t_can.expire() is False
    with pytest.raises(IllegalStateTransitionError, match="Cannot expire ticket in state CANCELLED"):
        t_can.expire(raise_on_error=True)


def test_verify_token_edge_cases():
    now = time.time()
    ticket = Ticket("Tester", 10.0, "R-101", created_at=now, validity_seconds=1000)
    ticket.pay(MockSuccessGateway(), current_time=now)

    # Cancelled ticket token verification should return False
    ticket.cancel()
    assert ticket.verify_token(ticket.verification_hash) is False
