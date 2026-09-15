import pytest
from src.fare import calculate_base_fare

# =====================================================================
# 1. Equivalence Partitioning (EP) Tests
# =====================================================================

def test_fare_ep_valid_partitions():
    """Valid EP Partitions: Infant/Child (0-5), Student (6-17), Adult (18-64), Senior (65-120)."""
    # Infant / Child partition
    assert calculate_base_fare(0) == 0.0
    assert calculate_base_fare(3) == 0.0
    assert calculate_base_fare(5) == 0.0

    # Student / Youth partition
    assert calculate_base_fare(6) == 10.0
    assert calculate_base_fare(12) == 10.0
    assert calculate_base_fare(17) == 10.0

    # Adult Standard partition
    assert calculate_base_fare(18) == 25.0
    assert calculate_base_fare(35) == 25.0
    assert calculate_base_fare(64) == 25.0

    # Senior Fare partition
    assert calculate_base_fare(65) == 15.0
    assert calculate_base_fare(70) == 15.0
    assert calculate_base_fare(120) == 15.0


def test_fare_ep_invalid_partitions_out_of_range():
    """Invalid EP Partitions: Negative ages and extreme upper bounds (>120)."""
    # Negative age values
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(-1)
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(-5)
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(-100)

    # Upper bound exceedances (>120)
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(121)
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(125)
    with pytest.raises(ValueError, match="Invalid age"):
        calculate_base_fare(200)


def test_fare_ep_invalid_partitions_types():
    """Invalid EP Partitions: Non-integer types (strings, floats, booleans, None)."""
    # String inputs
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare("25")
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare("abc")

    # Float inputs
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare(25.5)
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare(0.5)

    # Boolean inputs (Python bool is subclass of int, defensive check MUST block bool)
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare(True)
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare(False)

    # None and container types
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare(None)
    with pytest.raises(TypeError, match="expected integer"):
        calculate_base_fare([25])


def test_fare_ep_distance_and_zone_multipliers():
    """EP Partitions for Distance & Zone Multipliers."""
    # Local route (default multiplier 1.0)
    assert calculate_base_fare(35, route_type="local") == 25.0

    # Express / Inter-Subcity route (default express multiplier 1.5)
    assert calculate_base_fare(35, route_type="express") == 37.5
    assert calculate_base_fare(35, route_type="inter-subcity") == 37.5

    # Child fare remains free (0.0) regardless of zone multiplier
    assert calculate_base_fare(3, route_type="express", zone_multiplier=2.0) == 0.0

    # Custom zone multiplier
    assert calculate_base_fare(35, zone_multiplier=2.0) == 50.0

    # Distance multiplier scaling
    assert calculate_base_fare(35, distance_km=50.0) == 37.5


def test_fare_invalid_multiplier_parameters():
    """Defensive validation for invalid multiplier parameters."""
    with pytest.raises(ValueError, match="must be greater than 0"):
        calculate_base_fare(25, zone_multiplier=0)
    with pytest.raises(ValueError, match="must be greater than 0"):
        calculate_base_fare(25, zone_multiplier=-1.5)
    with pytest.raises(TypeError, match="expected number"):
        calculate_base_fare(25, zone_multiplier="1.5")

    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_base_fare(25, distance_km=-5.0)
    with pytest.raises(TypeError, match="expected number"):
        calculate_base_fare(25, distance_km="10")

    with pytest.raises(TypeError, match="expected string"):
        calculate_base_fare(25, route_type=123)


# =====================================================================
# 2. Boundary Value Analysis (BVA) Tests
# =====================================================================

def test_fare_bva_2_value_boundaries():
    """Formal 2-Value BVA Test Cases around boundary points (0, 5, 6, 17, 18, 64, 65, 120)."""
    # Boundary 0 (Min valid age)
    with pytest.raises(ValueError):
        calculate_base_fare(-1)
    assert calculate_base_fare(0) == 0.0

    # Boundary 5 (Child upper bound) / 6 (Student lower bound)
    assert calculate_base_fare(5) == 0.0
    assert calculate_base_fare(6) == 10.0

    # Boundary 17 (Student upper bound) / 18 (Adult lower bound)
    assert calculate_base_fare(17) == 10.0
    assert calculate_base_fare(18) == 25.0

    # Boundary 64 (Adult upper bound) / 65 (Senior lower bound)
    assert calculate_base_fare(64) == 25.0
    assert calculate_base_fare(65) == 15.0

    # Boundary 120 (Max valid age)
    assert calculate_base_fare(120) == 15.0
    with pytest.raises(ValueError):
        calculate_base_fare(121)


def test_fare_bva_3_value_boundaries():
    """Formal 3-Value BVA Test Cases (Boundary - 1, Boundary, Boundary + 1)."""
    # 3-Value around boundary 0: -1 (invalid), 0 (valid child), 1 (valid child)
    with pytest.raises(ValueError):
        calculate_base_fare(-1)
    assert calculate_base_fare(0) == 0.0
    assert calculate_base_fare(1) == 0.0

    # 3-Value around boundary 5: 4 (child), 5 (child), 6 (student)
    assert calculate_base_fare(4) == 0.0
    assert calculate_base_fare(5) == 0.0
    assert calculate_base_fare(6) == 10.0

    # 3-Value around boundary 6: 5 (child), 6 (student), 7 (student)
    assert calculate_base_fare(5) == 0.0
    assert calculate_base_fare(6) == 10.0
    assert calculate_base_fare(7) == 10.0

    # 3-Value around boundary 17: 16 (student), 17 (student), 18 (adult)
    assert calculate_base_fare(16) == 10.0
    assert calculate_base_fare(17) == 10.0
    assert calculate_base_fare(18) == 25.0

    # 3-Value around boundary 18: 17 (student), 18 (adult), 19 (adult)
    assert calculate_base_fare(17) == 10.0
    assert calculate_base_fare(18) == 25.0
    assert calculate_base_fare(19) == 25.0

    # 3-Value around boundary 64: 63 (adult), 64 (adult), 65 (senior)
    assert calculate_base_fare(63) == 25.0
    assert calculate_base_fare(64) == 25.0
    assert calculate_base_fare(65) == 15.0

    # 3-Value around boundary 65: 64 (adult), 65 (senior), 66 (senior)
    assert calculate_base_fare(64) == 25.0
    assert calculate_base_fare(65) == 15.0
    assert calculate_base_fare(66) == 15.0

    # 3-Value around boundary 120: 119 (senior), 120 (senior), 121 (invalid)
    assert calculate_base_fare(119) == 15.0
    assert calculate_base_fare(120) == 15.0
    with pytest.raises(ValueError):
        calculate_base_fare(121)
