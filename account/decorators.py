from django.shortcuts import redirect
from django.contrib import messages

def email_verified_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.email_verified:
            messages.warning(request, "برای دسترسی باید ایمیل خود را تأیید کنید")
            return redirect('verify-email', pk=request.user.pk)
        return view_func(request, *args, **kwargs)
    return wrapper