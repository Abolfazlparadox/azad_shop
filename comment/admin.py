# comment/admin.py

from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.db import models
from .models import Comment

from .models import Comment


class CommentInline(GenericTabularInline):
    """
    Inline for replies under parent comments.
    """
    model = Comment
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 0
    readonly_fields = ('user', 'content', 'rating', 'likes', 'is_approved', 'created_at')
    fields = ('user', 'content', 'rating', 'likes', 'is_approved', 'created_at')
    show_change_link = True

class UniversityAccessAdmin(admin.ModelAdmin):
    """کلاس پایه برای دسترسی مبتنی بر دانشگاه"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs.select_related('user', 'content_type')

        # Fixed membership fetching
        membership = request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
        if not membership:
            return qs.none()
        user_university = membership.university

        from blog.models import BlogPost
        from product.models import Product
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q

        queries = []

        blog_ct = ContentType.objects.get_for_model(BlogPost)
        blog_ids = BlogPost.objects.filter(university=user_university).values_list('id', flat=True)
        queries.append(Q(content_type=blog_ct, object_id__in=list(blog_ids)))

        product_ct = ContentType.objects.get_for_model(Product)
        product_ids = Product.objects.filter(university=user_university).values_list('id', flat=True)
        queries.append(Q(content_type=product_ct, object_id__in=list(product_ids)))

        if queries:
            combined_query = queries.pop()
            for q in queries:
                combined_query |= q
            qs = qs.filter(combined_query)
        else:
            qs = qs.none()

        return qs.distinct().select_related('user', 'content_type')

@admin.register(Comment)
class CommentAdmin(UniversityAccessAdmin):
    list_display = (
        'short_content', 'user', 'content_object',
        'rating', 'likes', 'is_approved', 'created_at'
    )
    list_filter = ('is_approved', 'rating', 'content_type', 'created_at')
    search_fields = ('content', 'user__username', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ['is_approved',]
    date_hierarchy = 'created_at'
    actions = ['approve_comments', 'disapprove_comments']
    list_select_related = ('user', 'content_type')

    fieldsets = (
        (None, {
            'fields': (
                'user', 'content_type', 'object_id',
                'parent', 'content', 'rating', 'likes'
            )
        }),
        (_('Status'), {
            'fields': ('is_approved',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = _('متن دیدگاه')

    @admin.action(description=_("تأیید دیدگاه‌های انتخاب‌شده"))
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, _('%(count)d دیدگاه تأیید شد.') % {'count': updated})

    @admin.action(description=_("رد دیدگاه‌های انتخاب‌شده"))
    def disapprove_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, _('%(count)d دیدگاه رد شد.') % {'count': updated})