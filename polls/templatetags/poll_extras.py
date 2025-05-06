from django.utils.translation import gettext_lazy as _
from django import template
from jalali_date import date2jalali
from datetime import datetime

register = template.Library()


@register.filter(name='cut')
def cut(value, arg):
    """Removes all values of arg from the given string"""
    return value.replace(arg, '')

# register.filter("cut", cut)

@register.filter(name='show_jalali_date')
def show_jalali_date(value):
    if not value:
        return ""
    try:
        return date2jalali(value).strftime('%Y/%m/%d')
    except Exception:
        return value  # یا نمایش پیش‌فرض

@register.filter(name='three_digits_currency')
def three_digits_currency(value: int):
    return '{:,}'.format(value) + _('Toman')


@register.simple_tag
def multiply(quantity, price, *args, **kwargs):
    return three_digits_currency(quantity * price)
