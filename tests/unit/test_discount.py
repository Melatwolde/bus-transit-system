from itertools import product

import pytest

from src.discount import calculate_discount_rate, is_peak_hour


def test_legacy_decision_table_covers_all_eight_combinations():
	expected = {
		(False, False, False): 15,
		(False, False, True): 20,
		(False, True, False): 25,
		(False, True, True): 30,
		(True, False, False): 0,
		(True, False, True): 20,
		(True, True, False): 10,
		(True, True, True): 30,
	}
	for is_peak, is_frequent, is_holiday in product((False, True), repeat=3):
		assert calculate_discount_rate(is_peak, is_frequent, is_holiday) == expected[
			(is_peak, is_frequent, is_holiday)
		]


def test_peak_boundaries_are_start_inclusive_and_end_exclusive():
	assert is_peak_hour("07:00")
	assert is_peak_hour("08:59")
	assert not is_peak_hour("09:00")
	assert is_peak_hour("17:00")
	assert is_peak_hour("18:59")
	assert not is_peak_hour("19:00")


@pytest.mark.parametrize("is_peak, is_frequent, is_holiday, is_weekend, is_student", product((False, True), repeat=5))
def test_modern_rules_cover_all_32_combinations(
	is_peak, is_frequent, is_holiday, is_weekend, is_student
):
	base = 10 if is_peak and is_frequent else 0 if is_peak else 25 if is_frequent else 15
	expected = min(base + (5 if is_holiday else 0) + (5 if is_weekend else 0) + (10 if is_student else 0), 40)
	assert calculate_discount_rate(
		is_peak=is_peak,
		is_frequent_rider=is_frequent,
		is_holiday=is_holiday,
		is_weekend=is_weekend,
		is_student=is_student,
	) == expected


def test_time_of_day_derives_peak_status():
	assert calculate_discount_rate(time_of_day="07:30", is_frequent_rider=True) == 10
	assert calculate_discount_rate(time_of_day="12:30", is_frequent_rider=True) == 25


def test_discount_cap_validation():
	with pytest.raises(ValueError):
		calculate_discount_rate(is_peak=False, discount_cap=-1)
	with pytest.raises(ValueError):
		calculate_discount_rate(is_peak=False, discount_cap=101)
	with pytest.raises(TypeError):
		calculate_discount_rate(is_peak=False, discount_cap=40.0)
