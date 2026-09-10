from src.discount import calculate_discount_rate

def test_decision_table_rules():
    assert calculate_discount_rate(is_peak=True, is_frequent_rider=True, is_holiday=True) == 30
    assert calculate_discount_rate(is_peak=False, is_frequent_rider=False, is_holiday=True) == 20
    assert calculate_discount_rate(is_peak=True, is_frequent_rider=True, is_holiday=False) == 10
    assert calculate_discount_rate(is_peak=True, is_frequent_rider=False, is_holiday=False) == 0
    assert calculate_discount_rate(is_peak=False, is_frequent_rider=True, is_holiday=False) == 25
    assert calculate_discount_rate(is_peak=False, is_frequent_rider=False, is_holiday=False) == 15
