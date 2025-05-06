# unit_admin/admin.py

from django.core.paginator import Paginator
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import render, redirect, get_object_or_404
from product.models import Product
from account.models import User, Membership
from django.contrib import admin, messages
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError, PermissionDenied

from unit_admin.forms import CustomUserCreationForm



# 1. ایجاد فرم لاگین سفارشی بدون نیاز به is_staff
class CustomAdminAuthForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        """اجازه لاگین به کاربران غیر-استاف"""
        if not user.is_active:
            raise ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )
        # حذف چک is_staff


# 2. تنظیمات پنل ادمین سفارشی
class UnitAdminSite(admin.AdminSite):
    name = 'unit_admin'
    site_header = "پنل مدیریت دبیر رفاهی"
    site_title = "مدیریت دانشگاهی"
    index_title = "داشبورد"
    index_template = "unit_admin/index.html"
    login_template = "account/login.html"
    logout_template = "account/logout.html"
    login_form = CustomAdminAuthForm

    def has_permission(self, request):
        """بررسی دسترسی بر اساس نقش دبیر رفاهی"""
        return (
                request.user.is_authenticated and
                request.user.memberships.filter(
                    role='OFFI',
                    is_confirmed=True,
                    university__isnull=False
                ).exists()
        )

    def login(self, request, extra_context=None):
        """مدیریت فرآیند لاگین"""
        # کاربر لاگین کرده اما دسترسی ندارد
        if request.user.is_authenticated and not self.has_permission(request):
            return HttpResponseRedirect(reverse('403'))

        # فراخوانی لاگین اصلی با تنظیمات سفارشی
        return super().login(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('users/', self.admin_view(self.user_list_view), name='user_list'),
            path('users/add/', self.admin_view(self.add_user_view), name='add_user'),
            path('roles/', self.admin_view(self.role_list_view), name='role_list'),
            path('roles/delete/', self.admin_view(self.delete_role), name='delete_role'),
            # path('users/<int:pk>/', self.admin_view(self.user_detail_view), name='user_detail'),
            # path('users/<int:pk>/edit/', self.admin_view(self.edit_user_view), name='edit_user'),
            # path('users/<int:pk>/delete/', self.admin_view(self.delete_user_view), name='delete_user'),
        ]
        return custom_urls + urls

    def role_list_view(self, request):
        # Get the current unit officer's university
        university = request.user.memberships.get(role='OFFI').university

        # Get confirmed memberships for the university
        memberships = Membership.objects.filter(
            university=university,
        ).exclude(user__id=request.user.id).distinct()

        # Pagination
        paginator = Paginator(memberships, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return TemplateResponse(request, 'unit_admin/all-roll.html', {
            **self.each_context(request),
            'memberships': page_obj,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
        })

    def delete_role(self, request):
        if request.method == 'POST':
            role_id = request.POST.get('role_id')
            try:
                # Get the current admin's university
                admin_membership = request.user.memberships.get(role='OFFI')
                university = admin_membership.university

                # Get and delete the membership
                membership = get_object_or_404(
                    Membership,
                    id=role_id,
                    university=university
                )
                membership.delete()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'نقش با موفقیت حذف شد'
                    })

                messages.success(request, "نقش با موفقیت حذف شد")
                return redirect('unit_admin:role_list')

            except Membership.DoesNotExist:
                messages.error(request, "نقش مورد نظر یافت نشد")
                return redirect('unit_admin:role_list')

        return redirect('unit_admin:role_list')

    def delete_user(request):
        if request.method == 'POST':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            user.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            return redirect('user_list')
        return redirect('user_list')

    def user_list_view(self, request):
        try:
            # Get current user's university membership
            admin_membership = request.user.memberships.get(role='OFFI')
            university = admin_membership.university

            # Get users with confirmed memberships in the same university
            user_list = User.objects.filter(
                memberships__university=university,
                memberships__is_confirmed=True
            ).exclude(id=request.user.id).distinct()

            # Pagination
            paginator = Paginator(user_list, 3)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            return TemplateResponse(request, 'unit_admin/all-users.html', {
                **self.each_context(request),
                'users': page_obj,
                'page_obj': page_obj,
                'is_paginated': page_obj.has_other_pages(),
            })

        except Membership.DoesNotExist:
            raise PermissionDenied("شما دسترسی لازم را ندارید")

    def add_user_view(self, request):
        if request.method == 'POST':
            form = CustomUserCreationForm(request.POST, request.FILES)
            if form.is_valid():
                user = form.save()
                messages.success(request, f"کاربر {user.username} با موفقیت ایجاد شد")
                return redirect('unit_admin:user_list')
            else:
                messages.error(request, "لطفا خطاهای فرم را برطرف کنید")
        else:
            form = CustomUserCreationForm()

        return render(request, 'unit_admin/add-new-user.html', {
            'form': form,
            **self.each_context(request),
        })
# ایجاد نمونه از کلاس
unit_admin = UnitAdminSite(name='unit_admin')



