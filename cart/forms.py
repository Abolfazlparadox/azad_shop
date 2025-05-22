from django import forms
from .models import Order
from django_jalali import AdminJalaliDateTimeWidget
from import_export.admin import ImportExportModelAdmin
from jalali_date.admin import ModelAdminJalaliMixin
from django.contrib import admin

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'
        widgets = {
            'created_at': AdminJalaliDateTimeWidget,
        }

@admin.register(Order)
class OrderAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    form = OrderAdminForm
    # ... بقیه تنظیمات قبلی شما ...
