import pytest
from src.fare import calculate_base_fare

def test_fare_ep_partitions():
    assert calculate_base_fare(3) == 0.0
    assert calculate_base_fare(12) == 10.0
    assert calculate_base_fare(35) == 25.0
    assert calculate_base_fare(70) == 15.0

def test_fare_ep_invalid_partitions():
    with pytest.raises(ValueError):
        calculate_base_fare(-5)
    with pytest.raises(ValueError):
        calculate_base_fare(125)

def test_fare_bva_boundaries():
    with pytest.raises(ValueError):
        calculate_base_fare(-1)
    assert calculate_base_fare(0) == 0.0
    assert calculate_base_fare(5) == 0.0
    assert calculate_base_fare(6) == 10.0
    assert calculate_base_fare(17) == 10.0
    assert calculate_base_fare(18) == 25.0
    assert calculate_base_fare(64) == 25.0
    assert calculate_base_fare(65) == 15.0
    assert calculate_base_fare(120) == 15.0
    with pytest.raises(ValueError):
        calculate_base_fare(121)
