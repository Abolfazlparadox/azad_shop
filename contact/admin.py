# contact/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Subject, ContactMessage

@admin.register(Subject)
class ContactSubjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')       # فقط فیلدهای واقعی
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)
    ordering = ('title',)
    # متادیتای تاریخ در مدل نیست → حذف readonly_fields و list_filter
    # readonly_fields = ()
    # list_filter = ()


@admin.action(description=_("Mark selected messages as answered"))
def make_answered(modeladmin, request, queryset):
    updated = queryset.update(is_answered=True)
    modeladmin.message_user(
        request,
        _("%d پیام به‌عنوان پاسخ‌داده‌شده علامت‌گذاری شد.") % updated
    )


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'subject', 'full_name', 'email',
        'university', 'status', 'created_at'
    )
    list_display_links = ('id', 'full_name')
    list_filter = ('subject', 'university', 'status')
    search_fields = ('first_name', 'last_name', 'email', 'message')
    autocomplete_fields = ('subject', 'university')
    readonly_fields = ('created_at',)
    actions = [make_answered]
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('فرستنده'), {
            'fields': (('first_name', 'last_name'), 'email', 'phone_number', 'university'),
        }),
        (_('جزئیات پیام'), {
            'fields': ('subject', 'message'),
        }),
        (_('وضعیت'), {
            'fields': ('status',),
            'classes': ('collapse',),
        }),
        (_('زمان‌ها'), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = _('نام و نام‌خانوادگی')
