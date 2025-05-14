from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from university.models import University

class Subject(models.Model):
    title = models.CharField(max_length=200, unique=True, verbose_name=_('موضوع'))
    slug  = models.SlugField(max_length=200, unique=True, allow_unicode=True, verbose_name=_('شناسه URL'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('موضوع تماس')
        verbose_name_plural = _('موضوعات تماس')

class ContactMessage(models.Model):
    STATUS_CHOICES = [
        ('pending',  _('در انتظار')),
        ('answered', _('پاسخ‌داده‌شده')),
    ]

    first_name     = models.CharField(max_length=100, verbose_name=_('نام'))
    last_name      = models.CharField(max_length=100, verbose_name=_('نام‌خانوادگی'))
    email          = models.EmailField(verbose_name=_('ایمیل'))
    phone_number   = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('تلفن'))
    subject        = models.ForeignKey(Subject, on_delete=models.SET_NULL,
                                       null=True, blank=True, verbose_name=_('موضوع'))
    other_subject  = models.CharField(max_length=200, blank=True, verbose_name=_('موضوع دیگر'))
    message        = models.TextField(verbose_name=_('متن پیام'))
    answer =models.TextField(verbose_name=_('متن پاسخ'),blank=True, null=True)
    attachment     = models.FileField(upload_to='contact/attachments/', blank=True, null=True,
                                      verbose_name=_('ضمیمه'))
    university     = models.ForeignKey(University, on_delete=models.SET_NULL,
                                       null=True, blank=True, verbose_name=_('دانشگاه'))
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES,
                                      default='pending', verbose_name=_('وضعیت'))
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ارسال'))
    responded_at   = models.DateTimeField(blank=True, null=True, verbose_name=_('تاریخ پاسخ'))

    class Meta:
        verbose_name = _('پیام تماس')
        verbose_name_plural = _('پیام‌های تماس')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.get_status_display()}"
