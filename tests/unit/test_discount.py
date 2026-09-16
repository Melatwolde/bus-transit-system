import pytest
from datetime import datetime, time
from zoneinfo import ZoneInfo
from src.discount import calculate_discount_rate, is_peak_hour


def test_is_peak_hour():
    # Test time object inputs
    assert is_peak_hour(time(14, 0)) is True
    assert is_peak_hour(time(18, 0)) is True
    assert is_peak_hour(time(10, 0)) is False

    # Test string ISO inputs
    assert is_peak_hour("14:30:00") is True
    assert is_peak_hour("10:00:00") is False

    # Test datetime object inputs
    dt_peak = datetime(2026, 9, 16, 14, 30, tzinfo=ZoneInfo("Africa/Addis_Ababa"))
    dt_off_peak = datetime(2026, 9, 16, 10, 0, tzinfo=ZoneInfo("Africa/Addis_Ababa"))
    assert is_peak_hour(dt_peak) is True
    assert is_peak_hour(dt_off_peak) is False


def test_legacy_calculate_discount_rate():
    # Single positional arg (is_peak)
    assert calculate_discount_rate(True) == 0
    assert calculate_discount_rate(False) == 15

    # Two positional args (is_peak, is_frequent_rider)
    assert calculate_discount_rate(True, True) == 10
    assert calculate_discount_rate(False, True) == 25

    # Three positional args (is_peak, is_frequent_rider, is_holiday)
    assert calculate_discount_rate(False, True, True) == 30
    assert calculate_discount_rate(False, False, True) == 20
    assert calculate_discount_rate(False, False, False) == 15

    # More than 3 positional args raises TypeError
    with pytest.raises(TypeError, match="accepts at most 3 positional arguments"):
        calculate_discount_rate(True, False, False, True)


def test_discount_cap_validation():
    # Invalid discount_cap type
    with pytest.raises(TypeError, match="discount_cap must be an integer"):
        calculate_discount_rate(discount_cap="40")

    with pytest.raises(TypeError, match="discount_cap must be an integer"):
        calculate_discount_rate(discount_cap=True)

    # Out of range discount_cap
    with pytest.raises(ValueError, match="discount_cap must be between 0 and 100"):
        calculate_discount_rate(discount_cap=-1)

    with pytest.raises(ValueError, match="discount_cap must be between 0 and 100"):
        calculate_discount_rate(discount_cap=101)


def test_modern_keyword_calculate_discount_rate():
    # Default keyword params
    assert calculate_discount_rate() == 15

    # Peak hour & frequent rider keywords
    assert calculate_discount_rate(is_peak=True, is_frequent_rider=True) == 10
    assert calculate_discount_rate(is_peak=True, is_frequent_rider=False) == 0
    assert calculate_discount_rate(is_peak=False, is_frequent_rider=True) == 25

    # Time of day inference
    assert calculate_discount_rate(time_of_day="14:00:00", is_frequent_rider=True) == 10
    assert calculate_discount_rate(time_of_day="10:00:00", is_frequent_rider=False) == 15

    # Stacking discounts (holiday +5%, weekend +5%, student +10%)
    # Base 25 (frequent) + 5 (holiday) + 5 (weekend) + 10 (student) = 45 -> Capped at 40
    assert calculate_discount_rate(
        is_frequent_rider=True,
        is_holiday=True,
        is_weekend=True,
        is_student=True
    ) == 40

    # Custom discount cap
    assert calculate_discount_rate(
        is_student=True,
        is_holiday=True,
        discount_cap=20
    ) == 20
