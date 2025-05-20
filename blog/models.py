from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from product.models import ProductCategory
from university.models import University


class BlogPost(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('عنوان'))
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name=_('شناسه URL'))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts',
        verbose_name=_('نویسنده')
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts',
        verbose_name=_('دسته‌بندی محصول')
    )
    short_content = models.TextField(max_length=500, verbose_name=_('محتوای کوتاه'))
    full_content = models.TextField(verbose_name=_('محتوای کامل'))
    banner_image = models.ImageField(
        upload_to='blog/banners/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('تصویر بنر')
    )
    tags = models.ManyToManyField(
        'home.Tag',
        blank=True,
        related_name='blog_posts',
        verbose_name=_('تگ‌ها')
    )
    is_published = models.BooleanField(default=False, verbose_name=_('منتشر شده'))
    published_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاریخ انتشار'))
    views = models.PositiveIntegerField(default=0, verbose_name=_('تعداد بازدید'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ایجاد'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاریخ بروزرسانی'))
    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('دانشگاه')
    )
    class Meta:
        verbose_name = _('پست وبلاگ')
        verbose_name_plural = _('پست‌های وبلاگ')
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-published_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
    def get_absolute_url(self):
        return reverse('single_post', kwargs={'slug': self.slug})
    def __str__(self):
        return self.title
