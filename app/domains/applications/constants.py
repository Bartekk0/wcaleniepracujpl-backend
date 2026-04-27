ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "submitted": {"reviewing"},
    "reviewing": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}

