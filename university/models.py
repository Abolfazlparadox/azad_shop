from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django_extensions.db.fields import AutoSlugField
from iranian_cities.models import Province, City

def validate_university_name(value):
    required_prefix = "دانشگاه آزاد "
    if not value.startswith(required_prefix):
        raise ValidationError(
            f"نام دانشگاه باید با '{required_prefix}' شروع شود"
        )
class University(models.Model):
    # اطلاعات پایه
    name = models.CharField(
        _('نام دانشگاه'),
        max_length=200,
        unique=True,
        db_index=True,
        validators=[validate_university_name],
        help_text=_("نام باید با 'دانشگاه آزاد' شروع شود")
    )
    established_date = models.DateField(
        _('تاریخ تأسیس'),
        db_index=True
    )
    slug = AutoSlugField(
        populate_from='name',
        unique=True,
        db_index=True
    )
    # اطلاعات مکانی
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        verbose_name=_('استان'),  # Persian for 'Province'
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name=_('شهر'),  # Persian for 'City'
        null=True,
        blank=True,
    )
    address = models.CharField(
        _('آدرس'),
        max_length=200,
        db_index=True
    )
    post_code = models.CharField(
        _('کد پستی'),
        max_length=200,
        db_index=True
    )
    # اطلاعات تماس
    phone_number = models.CharField(
        _('شماره تماس'),
        max_length=15,
        db_index=True
    )
    email = models.EmailField(
        _('ایمیل رسمی'),
        db_index=True
    )
    website = models.URLField(
        _('آدرس وبسایت'),
        validators=[URLValidator()]
    )
    # وضعیت
    status = models.BooleanField(
        _('وضعیت'),
        default=False

    )
    # توصیفات
    description = models.TextField(
        verbose_name=_('توضیحات کامل'),
        null=True, blank=True
    )
    logo = models.ImageField(
        _('لوگو'),
        upload_to='university/logos/',
        blank=True,
        null=True
    )
    class Meta:
        verbose_name = _('دانشگاه')
        verbose_name_plural = _('دانشگاه‌ها')
        ordering = ['name']

    def save(self, *args, **kwargs):
        required_prefix = "دانشگاه آزاد "

        if not self.name.startswith(required_prefix):
            self.name = f"{required_prefix}{self.name}"

        # حذف پیشوندهای تکراری (اگر وجود داشته باشد)
        self.name = self.name.replace(
            required_prefix,
            '',
            self.name.count(required_prefix) - 1
        ).strip()

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name} ({self.city})"
