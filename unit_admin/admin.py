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
from django.core.exceptions import ValidationError

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
            return HttpResponseRedirect(reverse('access_denied'))

        # فراخوانی لاگین اصلی با تنظیمات سفارشی
        return super().login(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('users/', self.admin_view(self.user_list_view), name='user_list'),
            path('users/add/', self.admin_view(self.add_user_view), name='add_user'),
            path('roles/', self.admin_view(self.role_list_view), name='role_list'),
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
            is_confirmed=True
        ).select_related('user').order_by('-confirmed_at')

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
            membership = get_object_or_404(
                Membership,
                id=role_id,
                university=request.user.memberships.get(role='OFFI').university
            )
            membership.delete()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
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
        # فیلتر کاربران بر اساس دانشگاه
        university = request.user.memberships.get(role='OFFI').university
        user_list = User.objects.filter(memberships__university=university)

        # صفحه‌بندی
        paginator = Paginator(user_list, 3)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return TemplateResponse(request, 'unit_admin/all-users.html', {
            **self.each_context(request),
            'users': page_obj,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
        })

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


@admin.register(User, site=unit_admin)
class UserAdmin(admin.ModelAdmin):
    list_display = ('profile_image', 'full_name', 'mobile', 'email', 'university', 'role_status')
    list_display_links = ('full_name',)
    search_fields = ('first_name', 'last_name', 'mobile')
    list_filter = ('memberships__role',)

    def get_queryset(self, request):
        # فیلتر کاربران بر اساس دانشگاه دبیر رفاهی
        qs = super().get_queryset(request)
        if request.user.has_perm('account.view_user'):
            university = request.user.memberships.filter(role='OFFI').first().university
            return qs.filter(memberships__university=university)
        return qs.none()

    def university(self, obj):
        return obj.memberships.first().university.name if obj.memberships.exists() else '-'

    university.short_description = 'دانشگاه'

    def role_status(self, obj):
        membership = obj.memberships.first()
        if membership:
            return f"{membership.get_role_display()} ({'فعال' if membership.is_confirmed else 'غیرفعال'})"
        return '-'

    role_status.short_description = 'وضعیت نقش'

    def profile_image(self, obj):
        if obj.profile.image:
            return format_html('<img src="{}" class="user-thumbnail">', obj.profile.image.url)
        return format_html('<div class="default-avatar">{}</div>', obj.first_name[0])

    profile_image.short_description = 'تصویر'

@admin.register(Product, site=unit_admin)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'university', 'price')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(university=request.user.university)


