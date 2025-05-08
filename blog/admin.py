# blog/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(ImportExportModelAdmin,admin.ModelAdmin):
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

