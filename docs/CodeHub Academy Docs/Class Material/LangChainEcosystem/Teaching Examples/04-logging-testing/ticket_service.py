# Ticket scoring system: assigns numerical scores based on priority and reopens
# The base score comes from the priority level, then reopen count is added to increase urgency

PRIORITY_SCORES = {"low": 1, "high": 3}


def calculate_score(priority: str, reopens: int = 0) -> int:
    """Calculate ticket score by adding reopens to the base priority score."""

    # 1. Έλεγχος για λάθος τύπο δεδομένων (για το TypeError test)
    if not isinstance(reopens, int):
        raise TypeError("reopens must be an integer")

    # 2. Έλεγχος για αρνητικό αριθμό (για το ValueError test)
    if reopens < 0:
        raise ValueError("reopens cannot be negative")

    return PRIORITY_SCORES.get(priority, 0) + reopens
