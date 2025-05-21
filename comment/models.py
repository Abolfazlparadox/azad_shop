# comment/models.py
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _

class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('کاربر')
    )
    # Generic relation to any object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('نوع محتوا'),
        help_text=_('نوع مدلی که این دیدگاه به آن متصل است')
    )
    object_id = models.PositiveIntegerField(verbose_name=_('شناسه شی'),blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Threaded replies
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE,
        verbose_name=_('پاسخ به')
    )

    # Core comment fields
    content = models.TextField(verbose_name=_('متن دیدگاه'))
    rating = models.PositiveSmallIntegerField(
        choices=[(i, f'{i} ⭐') for i in range(1, 6)],
        null=True,
        blank=True,
        verbose_name=_('امتیاز')
    )
    likes = models.PositiveIntegerField(default=0, verbose_name=_('تعداد لایک'))

    # Moderation and metadata
    is_approved = models.BooleanField(default=False, verbose_name=_('تأیید شده'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))

    class Meta:
        verbose_name = _('دیدگاه')
        verbose_name_plural = _('دیدگاه‌ها')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user']),
            models.Index(fields=['parent']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user} on {self.content_type} (ID {self.object_id})"

    def approved_replies(self):
        return self.replies.filter(is_approved=True)
