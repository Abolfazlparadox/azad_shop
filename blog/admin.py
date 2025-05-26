# blog/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from .models import BlogPost
class UniversityAccessAdmin(admin.ModelAdmin):
    """کلاس پایه برای دسترسی مبتنی بر دانشگاه"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # اگر کاربر سوپر یوزر است همه چیز را ببینید
        if request.user.is_superuser:
            return qs

        membership = request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
        return qs.filter(university=membership.university) if membership else qs.none()

    def save_model(self, request, obj, form, change):
        # تنظیم خودکار دانشگاه هنگام ایجاد رکورد جدید
        if not change and not obj.university:
            membership = request.user.memberships.filter(
                role='OFFI',
                is_confirmed=True
            ).first()
            if membership:
                obj.university = membership.university
        super().save_model(request, obj, form, change)
@admin.register(BlogPost)
class BlogPostAdmin(ImportExportModelAdmin,UniversityAccessAdmin):
    list_display = (
        'title', 'author', 'category', 'is_published', 'published_at', 'views'
    )
    list_filter = (
        'is_published', 'category', 'author'
    )
    search_fields = (
        'title', 'short_content', 'full_content'
    )
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('tags',)
    date_hierarchy = 'published_at'
    readonly_fields = ('views', 'created_at', 'updated_at')
    list_select_related = ('author', 'category')
    ordering = ('-published_at',)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'category', 'tags')
        }),
        (_('Content'), {
            'fields': ('short_content', 'full_content', 'banner_image')
        }),
        (_('Publication'), {
            'fields': ('is_published', 'published_at')
        }),
        (_('Metadata'), {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author', 'category').prefetch_related('tags')

