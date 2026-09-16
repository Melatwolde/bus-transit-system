import pytest
from src.fleet import BusRoute

def test_bus_route_capacity():
    route = BusRoute("R-TEST", "A", "B", capacity=2)
    assert route.reserve_seat() == True
    assert route.reserve_seat() == True
    # At capacity
    assert route.reserve_seat() == False
