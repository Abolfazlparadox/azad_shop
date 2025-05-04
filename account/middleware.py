# middleware.py
from django.http import HttpResponseForbidden
from account.models import Membership


class UnitOfficerAccessControl:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # بررسی نقش کاربر
        if request.user.is_authenticated:
            if request.user.memberships.filter(
                    role='OFFI',
                    is_confirmed=True
            ).exists():
                # مسدود کردن دسترسی به ادمین پیشفرض
                if request.path.startswith('/admin/'):
                    return HttpResponseForbidden("""
                        دسترسی به پنل ادمین اصلی برای دبیران رفاهی ممنوع است.
                        از پنل اختصاصی استفاده کنید: /unit-admin/
                    """)

        return self.get_response(request)

class RealIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            request.META['REMOTE_ADDR'] = request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
        return self.get_response(request)

class VerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Clear verification flags after response
        if 'needs_verification' in request.session:
            del request.session['needs_verification']

        return response