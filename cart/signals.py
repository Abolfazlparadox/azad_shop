from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart

@receiver(user_logged_in)
def create_cart_on_login(sender, user, request, **kwargs):
    Cart.objects.get_or_create(user=user, is_paid=False)