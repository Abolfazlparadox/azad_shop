# account/signals.py
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Membership
from product.models import Product


@receiver(user_logged_in)
def update_last_login_ip(sender, request, user, **kwargs):
    """Update last_login_ip when user logs in"""
    ip = get_client_ip(request)
    if ip and user.last_login_ip != ip:
        user.last_login_ip = ip
        user.save(update_fields=['last_login_ip'])

def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
