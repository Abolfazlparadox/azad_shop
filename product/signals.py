from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Discount

@receiver(pre_save, sender=Discount)
def validate_discount_dates(sender, instance, **kwargs):
    """Ensures discount end date is after start date"""
    if instance.valid_to <= instance.valid_from:
        raise ValidationError("تاریخ پایان تخفیف باید بعد از تاریخ شروع باشد.")

