def calculate_discount_rate(is_peak: bool, is_frequent_rider: bool, is_holiday: bool) -> int:
    """
    Evaluates combinatorial rules:
      - Rule 1: Holiday + Frequent -> 30%
      - Rule 2: Holiday + Non-Frequent -> 20%
      - Rule 3: Peak + Frequent -> 10%
      - Rule 4: Peak + Non-Frequent -> 0%
      - Rule 5: Off-Peak + Frequent -> 25%
      - Rule 6: Off-Peak + Non-Frequent -> 15%
    """
    if is_holiday:
        return 30 if is_frequent_rider else 20
    if is_peak:
        return 10 if is_frequent_rider else 0
    return 25 if is_frequent_rider else 15
