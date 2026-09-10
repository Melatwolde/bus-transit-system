def calculate_base_fare(age: int) -> float:
    """Calculates ticket base fare using age bands."""
    if age < 0 or age > 120:
        raise ValueError("Invalid age: must be between 0 and 120")
    if age <= 5:
        return 0.0
    if age <= 17:
        return 10.0
    if age <= 64:
        return 25.0
    return 15.0