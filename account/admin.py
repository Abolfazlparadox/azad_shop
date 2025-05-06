# account/admin.py
from time import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from .models import User, Membership, Address

def _is_super_or_global_admin(user):
    return user.is_superuser or user.is_staff

@admin.register(User)
class UserAdminCustom(ImportExportModelAdmin, BaseUserAdmin):
    list_display = (
        'avatar_preview',
        'username',
        'full_name',
        'active_role_display',
        'is_active',
        'is_staff',
        'last_login',
    )
    list_select_related = ('province', 'city')
    list_filter = (
        'is_active',
        'is_staff',
        ('date_joined', admin.DateFieldListFilter),
    )
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'mobile', 'national_code'
    )
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('اطلاعات شخصی'), {
            'fields': (
                'avatar', 'first_name', 'last_name',
                'email', 'mobile', 'national_code', 'birthday'
            )
        }),
        (_('آدرس'), {
            'fields': ('province', 'city', 'address', 'postal_code')
        }),
        (_('مجوزها و گروه‌ها'), {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('تاریخ‌ها'), {
            'fields': ('last_login', 'date_joined')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('province', 'city')
        if not request.user.is_superuser:
            if request.user.memberships.filter(role='OFFI', is_confirmed=True).exists():
                # فیلتر بر اساس دانشگاه کاربر
                user_university = request.user.memberships.get(
                    role='OFFI',
                    is_confirmed=True
                ).university
                qs = qs.filter(memberships__university=user_university)
        return qs.distinct()

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;">',
                obj.avatar.url
            )
        return "-"
    avatar_preview.short_description = _('عکس')

    def has_module_permission(self, request):
        return _is_super_or_global_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return _is_super_or_global_admin(request.user)

    def has_change_permission(self, request, obj=None):
        if obj and obj == request.user:
            return True
        return _is_super_or_global_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):  # تغییر از GuardedModelAdmin به ModelAdmin
    actions = ['confirm_selected']
    list_display = ('user', 'university', 'role', 'is_confirmed', 'requested_at')
    list_filter = ('role', 'is_confirmed', 'university__city')
    search_fields = ('user__username', 'university__name')
    readonly_fields = ('requested_at', 'confirmed_at')

    def confirm_selected(self, request, queryset):
        updated = queryset.update(is_confirmed=True, confirmed_at=timezone.now())
        self.message_user(request, f"{updated} عضویت تأیید شد")

    confirm_selected.short_description = _("تأیید عضویت‌های انتخاب شده")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('university__city', 'user')
        if not request.user.is_superuser:
            if request.user.memberships.filter(role='OFFI', is_confirmed=True).exists():
                user_university = request.user.memberships.get(
                    role='OFFI',
                    is_confirmed=True
                ).university
                qs = qs.filter(university=user_university)
        return qs

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):  # تغییر از GuardedModelAdmin به ModelAdmin
    list_display = ('user', 'name', 'category', 'province', 'city', 'active')
    list_filter = ('province', 'city', 'active')
    search_fields = ('user__username', 'name', 'address')

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'province', 'city')
        if not request.user.is_superuser:
            if request.user.memberships.filter(role='OFFI', is_confirmed=True).exists():
                user_university = request.user.memberships.get(
                    role='OFFI',
                    is_confirmed=True
                ).university
                qs = qs.filter(user__memberships__university=user_university)
        return qs.distinct()

# @admin.register(Membership)
# class UnitMembershipAdmin(admin.ModelAdmin):
#     list_display = ('user', 'university', 'role', 'is_confirmed')
#
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         user_university = request.user.memberships.get(role='OFFI').university
#         return qs.filter(university=user_university)
#
#     def has_add_permission(self, request):
#         return False  # غیرفعال کردن ایجاد عضویت جدید در پنل واحد
#
#     def has_delete_permission(self, request, obj=None):
#         return False  #
