
def clamp(value: float | int, min_value: float | int, max_value: float | int) -> float | int:
    """Clamp a number between a minimum and maximum value."""
    return max(min_value, min(value, max_value))
