def test_holiday_discount():
    from src.discount import calculate_discount_rate
    assert calculate_discount_rate(False, True, True) == 30
    assert calculate_discount_rate(False, False, True) == 20
