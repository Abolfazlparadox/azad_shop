# unit_admin/apps.py
from django.apps import AppConfig

class UnitAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unit_admin'

    def ready(self):
        # Import admin registrations
        from . import admin  # 