# unit_admin/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value: str, args: str) -> str:
    """
    جایگزینی یک زیررشته با زیررشتهٔ دیگر.
    Usage in template: {{ value|replace:"old,new" }}
    """
    try:
        old, new = args.split(',', 1)
    except ValueError:
        return value
    return value.replace(old, new)
