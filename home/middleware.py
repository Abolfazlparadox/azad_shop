# home/middleware.py
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse


class UnitAdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith('/unit-admin/'):
            if not request.user.is_authenticated:
                return HttpResponseRedirect(f"{reverse('admin:login')}?next={request.path}")