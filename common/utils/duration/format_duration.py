import datetime


def format_duration(seconds):
    """Formats a given number of seconds into a human-readable duration string up to hours.

    Args:
      seconds: The total number of seconds.

    Returns:
      A string representing the formatted duration.
    """

    time_delta = datetime.timedelta(seconds=seconds)

    # Calculate components
    years = time_delta.days // 365
    weeks = (time_delta.days % 365) // 7
    days = (time_delta.days % 365) % 7
    hours = time_delta.seconds // 3600

    # Build the formatted string
    components = []
    if years:
        components.append(f"{years} year{'s' if years != 1 else ''}")
    if weeks:
        components.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if days:
        components.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        components.append(f"{hours} hour{'s' if hours != 1 else ''}")

    return ", ".join(components) or "less than an hour"
