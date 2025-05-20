from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import jdatetime

class NotificationBase(models.Model):
    """
    مدل پایه برای همه اعلان‌ها.
    """
    title       = models.CharField(max_length=200, verbose_name=_('عنوان اعلان'))
    message     = models.TextField(verbose_name=_('متن اعلان'))
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد (شمسی)'))
    expired_at = models.DateTimeField(verbose_name=_('تاریخ ایجاد (شمسی)'),blank=True, null=True)
    class Meta:
        abstract = True

    def jalali_created(self):
        """تبدیل created_at به تاریخ جلالی"""
        return jdatetime.datetime.fromgregorian(datetime=self.created_at).strftime('%Y/%m/%d %H:%M')
    jalali_created.short_description = _('تاریخ ایجاد (جلالی)')

    def __str__(self):
        return self.title

class AdminNotification(NotificationBase):
    """
    اعلان‌های ویژه ادمین واحد (UNIT_OFFICER).
    هر رکورد برای یک درخواست یا رویداد خاص برای یک Membership از نوع OFFI.
    """
    membership = models.ForeignKey(
        'account.Membership',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'OFFI'},
        verbose_name=_('نقش پذیرنده اعلان'),
        related_name='admin_notifications'
    )
    is_read    = models.BooleanField(default=False, verbose_name=_('خوانده شد'))

    class Meta:
        verbose_name = _('اعلان ادمین')
        verbose_name_plural = _('اعلان‌های ادمین')
        ordering = ['-created_at']
