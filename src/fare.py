from typing import Union


def calculate_base_fare(
    age: int,
    route_type: str = "local",
    zone_multiplier: float = 1.0,
    distance_km: float = 0.0
) -> float:
    """Calculates ticket base fare using age bands, route types, and distance multipliers.

    Age Bands:
      - Infant/Child (0-5): 0.0 ETB (Free)
      - Student/Youth (6-17): 10.0 ETB (Concession)
      - Adult (18-64): 25.0 ETB (Standard)
      - Senior (65-120): 15.0 ETB (Senior fare)

    Strict Validation:
      - Rejects non-integers (strings, floats, booleans, None) with TypeError.
      - Rejects negative ages and ages > 120 with ValueError.
      - Rejects invalid zone_multiplier and distance_km types/values.
    """
    # Strict type validation for age
    if isinstance(age, bool) or not isinstance(age, int):
        raise TypeError(f"Invalid age type: expected integer, got {type(age).__name__}")

    # Strict range validation for age
    if age < 0 or age > 120:
        raise ValueError("Invalid age: must be between 0 and 120")

    # Type & range validation for zone_multiplier
    if isinstance(zone_multiplier, bool) or not isinstance(zone_multiplier, (int, float)):
        raise TypeError(f"Invalid zone_multiplier type: expected number, got {type(zone_multiplier).__name__}")
    if zone_multiplier <= 0:
        raise ValueError("Invalid zone_multiplier: must be greater than 0")

    # Type & range validation for distance_km
    if isinstance(distance_km, bool) or not isinstance(distance_km, (int, float)):
        raise TypeError(f"Invalid distance_km type: expected number, got {type(distance_km).__name__}")
    if distance_km < 0:
        raise ValueError("Invalid distance_km: cannot be negative")

    # Type validation for route_type
    if not isinstance(route_type, str):
        raise TypeError(f"Invalid route_type: expected string, got {type(route_type).__name__}")

    # Base fare calculation by age band
    if age <= 5:
        base = 0.0
    elif age <= 17:
        base = 10.0
    elif age <= 64:
        base = 25.0
    else:
        base = 15.0

    # Zone / route multiplier logic
    normalized_route = route_type.strip().lower()
    if normalized_route in ("express", "inter-subcity", "inter_subcity", "inter-city"):
        multiplier = 1.5 if zone_multiplier == 1.0 else zone_multiplier
    else:
        multiplier = zone_multiplier

    if distance_km > 0:
        multiplier *= (1.0 + (distance_km / 100.0))

    return round(base * multiplier, 2)