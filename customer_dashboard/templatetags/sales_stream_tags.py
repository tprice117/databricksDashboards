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


@register.filter(is_safe=True)
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
            return value.strftime("%b %d, %Y @ %I:%M %p") + " (CT)"
        else:
            return naturaltime(value)
    return value


@register.filter
def slice_after(value, delimiter):
    """
    Used to get the first value after a delimiter. For instance, `{{ "notes-12-id"|slice_after:"-" }}` returns "12".
    This is useful for extracting the id from a prefix.
    """
    try:
        return value.split(delimiter, 1)[1]
    except IndexError:
        return value


@register.filter(is_safe=True)
def render_file(file):
    """Render an image file. `width` and `height` are optional, expect value in pixels."""
    image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
    # Need a better way to ensure image size is correct.
    if any(file.name.lower().endswith(ext) for ext in image_extensions):
        style = "object-fit: cover; width:150px; height:150px; max-width: 100%; max-height: 100%;"
        return f'<img src="{file.url}" alt="{file.name}" style="{style}">'
    else:
        style = "object-fit: contain; font-size: 150px; width: 100%; height: 100%;"
        return f'<i class="fas fa-file position-relative" style="{style}"><p class="position-absolute text-white fs-3" style="top: 50%; left: 50%; transform: translate(-50%, -50%);">.{file.name.split(".")[-1]}</p></i>'
