from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.text import slugify


class SiteOption(models.Model):
    """An arbitrary “option”/feature you can toggle on the site."""
    name = models.CharField(max_length=100, unique=True, verbose_name=_('گزینه سایت'))
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True,
                            verbose_name=_('شناسه URL'))
    logo = models.FileField(upload_to='images/logo/options', verbose_name='لوگو',blank=True,)
    class Meta:
        verbose_name = _('گزینه سایت')
        verbose_name_plural = _('گزینه‌های سایت')
        ordering = ['name']

    def __str__(self):
        return self.name


class SiteSetting(models.Model):
    site_name       = models.CharField(max_length=200, verbose_name=_('نام سایت'))
    site_url        = models.CharField(max_length=200, verbose_name=_('دامنه سایت'))
    slogan          = models.CharField(
                           max_length=255,
                           verbose_name=_('شعار سایت'),
                           blank=True,
                           help_text=_('متن شعار نمایش داده‌شده در هدر یا فوتر')
                       )
    options         = models.ManyToManyField(
                           SiteOption,
                           verbose_name=_('گزینه‌های سایت'),
                           blank=True,
                           help_text=_('گزینه‌ها/ویژگی‌های فعال‌شده در سایت')
                       )
    site_logo       = models.ImageField(
                           upload_to='images/site.setting/',
                           verbose_name=_('لوگو اصلی سایت')
                       )
    secondary_logo  = models.ImageField(
                           upload_to='images/site.setting/',
                           verbose_name=_('لوگو دوم سایت'),
                           blank=True,
                           null=True,
                           help_text=_('لوگوی کوچک‌شده یا موبایل')
                       )
    address         = models.CharField(max_length=200, verbose_name=_('آدرس '))
    phone           = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('تلفن '))
    fax             = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('فکس '))
    email           = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('ایمیل '))
    copy_right      = models.TextField(verbose_name=_('متن کپی رایت  سایت'))
    about_us_text   = models.TextField(verbose_name=_('درباره سایت'))
    is_main_setting = models.BooleanField(verbose_name=_('تنظیمات اصلی'))

    class Meta:
        verbose_name = _('تنظیمات سایت')
        verbose_name_plural = _('تنظیمات سایت')

    def __str__(self):
        return self.site_name

class FooterLinkBox(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')

    class Meta:
        verbose_name = 'دسته بندی لینک‌های فوتر'
        verbose_name_plural = 'دسته بندی‌های لینک‌های فوتر'
        ordering = ['title']  # Order alphabetically

    def __str__(self):
        return self.title


class FooterLink(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')
    url = models.URLField(max_length=500, verbose_name='لینک')
    footer_link_box = models.ForeignKey(FooterLinkBox, on_delete=models.CASCADE, verbose_name='دسته بندی')

    class Meta:
        verbose_name = 'لینک فوتر'
        verbose_name_plural = 'لینک‌های فوتر'
        ordering = ['footer_link_box', 'title']
        indexes = [
            models.Index(fields=['footer_link_box']),
        ]

    def __str__(self):
        return self.title


class Slider(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')
    url = models.URLField(max_length=500, verbose_name='لینک')
    url_title = models.CharField(max_length=200, verbose_name='عنوان لینک')
    description = models.TextField(null=True, blank=True, verbose_name='توضیحات اسلایدر')
    image = models.ImageField(upload_to='images/sliders', verbose_name='تصویر اسلایدر')
    is_active = models.BooleanField(default=True, verbose_name='فعال / غیرفعال')
    # Optionally add an order field if you want to control slider sequence:
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')

    class Meta:
        verbose_name = 'اسلایدر'
        verbose_name_plural = 'اسلایدرها'
        ordering = ['order', 'id']  # Order first by custom order, then by id
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.title


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_('نام'))
    slug = models.SlugField(max_length=50, unique=True, allow_unicode=True, verbose_name=_('شناسه URL'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))

    class Meta:
        verbose_name = _('تگ')
        verbose_name_plural = _('تگ‌ها')
        ordering = ['name']
        indexes = [models.Index(fields=['slug'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name