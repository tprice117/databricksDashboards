from django import template

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
    return "${:,.2f}".format(value)
