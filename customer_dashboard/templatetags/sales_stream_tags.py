from datetime import datetime, timedelta
from django import template
from django.utils import timezone
from humanize import naturaltime

register = template.Library()


@register.filter(is_safe=True)
def add_markup(value, markup):
    """Discount is a percentage, e.g. 0-100. E.g. new_price = price * (1 + markup / 100)
    Ignore any errors and return the original value"""
    try:
        if markup == 0:
            return value
        else:
            return value * (1 + markup / 100)
    except Exception:
        return value


@register.filter(is_safe=True)
def currency(value):
    """Format a number as currency"""
    if value is None:
        return "$0.00"
    if not isinstance(value, float):
        try:
            value = float(value)
        except ValueError:
            return "$0.00"
    return "${:,.2f}".format(value)


@register.filter(is_safe=True)
def get_dict_value(dictionary, key):
    """Get a value from a dictionary"""
    return dictionary.get(key, None)


@register.filter
def downstream_naturaltime(value):
    """
    Return a humanized string representing time difference between now and the input value.

    If the input value is a datetime object and the difference is greater than 1 day, return the date in the format "%b %d, %Y (CT)".
    Otherwise, return the humanized string with the timezone "CT" (i.e. 3 seconds ago; 2 hours, 5 minutes ago; etc).
    """
    if not value:
        return ""
    now = timezone.now()
    if isinstance(value, datetime):
        if now - value > timedelta(days=1):
            return value.strftime("%b %d, %Y") + " (CT)"
        else:
            return naturaltime(value) + " (CT)"
    return value
