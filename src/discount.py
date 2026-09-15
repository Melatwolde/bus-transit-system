from datetime import time


DISCOUNT_CAP = 40


def is_peak_hour(time_of_day: str | time) -> bool:
    """Return whether a service time falls in either weekday peak window."""
    if isinstance(time_of_day, str):
        time_of_day = time.fromisoformat(time_of_day)
    return (time(7, 0) <= time_of_day < time(9, 0)) or (
        time(17, 0) <= time_of_day < time(19, 0)
    )


def calculate_discount_rate(
    *legacy_args: bool,
    is_peak: bool | None = None,
    is_frequent_rider: bool = False,
    is_holiday: bool = False,
    is_weekend: bool = False,
    is_student: bool = False,
    time_of_day: str | time | None = None,
    discount_cap: int = DISCOUNT_CAP,
) -> int:
    """Calculate a capped discount from the fare decision variables.

    The legacy three-argument form remains supported. Modern discounts stack:
    holiday and weekend each add 5%, students add 10%, and the result is
    limited by ``discount_cap``.
    """
    if len(legacy_args) > 3:
        raise TypeError("calculate_discount_rate accepts at most 3 positional arguments")
    if legacy_args:
        is_peak = legacy_args[0]
        if len(legacy_args) > 1:
            is_frequent_rider = legacy_args[1]
        if len(legacy_args) > 2:
            is_holiday = legacy_args[2]

    if isinstance(discount_cap, bool) or not isinstance(discount_cap, int):
        raise TypeError("discount_cap must be an integer")
    if not 0 <= discount_cap <= 100:
        raise ValueError("discount_cap must be between 0 and 100")

    if legacy_args:
        if is_holiday:
            return 30 if is_frequent_rider else 20
        if is_peak:
            return 10 if is_frequent_rider else 0
        return 25 if is_frequent_rider else 15

    peak = is_peak if is_peak is not None else (
        is_peak_hour(time_of_day) if time_of_day is not None else False
    )
    discount = 10 if peak and is_frequent_rider else 0 if peak else 25 if is_frequent_rider else 15
    if is_holiday:
        discount += 5
    if is_weekend:
        discount += 5
    if is_student:
        discount += 10
    return min(discount, discount_cap)
