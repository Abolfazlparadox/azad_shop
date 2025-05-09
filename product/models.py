from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.aggregates import Min, Max
from django.db.models import  F
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from account.models import User
from django.core.validators import MinValueValidator ,MaxValueValidator
from django.utils import timezone
import random
from django.db.models.signals import pre_save
from home.models import Tag
from university.models import University


class BaseModel(models.Model):
    """مدل پایه برای فیلدهای مشترک"""
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    is_active = models.BooleanField(default=False, db_index=True, verbose_name='فعال/غیرفعال')
    is_deleted = models.BooleanField(default=False, db_index=True, verbose_name='حذف شده/نشده')


    class Meta:
        abstract = True

class ProductCategory(BaseModel):
    title = models.CharField(max_length=300, unique=True, verbose_name='عنوان')
    slug = models.SlugField(max_length=300, unique=True, allow_unicode=True, verbose_name='شناسه URL')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='دسته‌بندی والد'
    )
    university = models.ForeignKey(University, on_delete=models.CASCADE, null=True, blank=True)
    icon = models.FileField(
        _('آیکون دسته‌بندی'),
        upload_to='category-icons/',
        blank=True, null=True,
        help_text=_('یک فایل SVG یا PNG برای این دسته‌بندی بارگذاری کنید')
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        indexes = [
            models.Index(fields=['slug']),
        ]

class ProductBrand(BaseModel):
    title = models.CharField(max_length=300, unique=True, verbose_name='نام برند')
    slug = models.SlugField(max_length=300, unique=True, allow_unicode=True, verbose_name='شناسه URL')
    logo = models.ImageField(upload_to='brands/logos/', null=True, blank=True, verbose_name='لوگو')
    university = models.ForeignKey(University, on_delete=models.CASCADE, null=True, blank=True)


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'

class Product(BaseModel):
    title = models.CharField(max_length=300, verbose_name='عنوان محصول')
    categories = models.ManyToManyField('ProductCategory', related_name='products', verbose_name='دسته‌بندی‌ها')
    main_image = models.ImageField(upload_to='products/main/%Y/%m/%d/', verbose_name='تصویر اصلی')
    brand = models.ForeignKey('ProductBrand', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='برند')
    sku = models.CharField(max_length=50, unique=True, db_index=True, verbose_name='کد محصول (SKU)', blank=True, null=True)
    short_description = models.TextField(max_length=500, verbose_name='توضیحات کوتاه')
    slug = models.SlugField(max_length=300, unique=True, allow_unicode=True, verbose_name='شناسه URL', db_index=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='وزن (کیلوگرم)')
    dimensions = models.CharField(max_length=50, blank=True, verbose_name='ابعاد (طول×عرض×ارتفاع)')
    tags = models.ManyToManyField(
            Tag,
            blank=True,
            related_name='products',
            verbose_name=_('تگ‌ها')
        )

    # Add foreign key to University
    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('دانشگاه')
    )

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=[ 'is_active']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['sku']),
        ]

    def save(self, *args, **kwargs):
        # Generate slug if not set
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)

        # Generate SKU if not set
        if not self.sku:
            # Create an abbreviation from the title: first letters of each word in uppercase
            abbreviation = ''.join(word[0] for word in self.title.split()).upper()
            # Generate a random 5-digit number
            random_digits = str(random.randint(10000, 99999))
            self.sku = abbreviation + random_digits

            # اطمینان از اینکه sku تکراری نباشه
            while Product.objects.filter(sku=self.sku).exists():
                random_digits = str(random.randint(10000, 99999))
                self.sku = abbreviation + random_digits

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product:product-detail', args=[self.slug])

    # @property
    # def current_price(self):
    #     return self.old_price if self.old_price and self.old_price < self.price else self.price

    def __str__(self):
        return f"{self.title} ({self.sku})"

class Discount(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='کد تخفیف')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    discount_type = models.CharField(max_length=10, choices=[
        ('percent', 'درصدی'),
        ('fixed', 'مبلغ ثابت'),
    ], verbose_name='نوع تخفیف')
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='مقدار تخفیف')
    max_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                       verbose_name='حداکثر تخفیف')
    valid_from = models.DateTimeField(verbose_name='تاریخ شروع')
    valid_to = models.DateTimeField(verbose_name='تاریخ پایان')
    max_usage = models.PositiveIntegerField(null=True, blank=True, verbose_name='حداکثر استفاده')
    used_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده شده')
    products = models.ManyToManyField(Product, blank=True, verbose_name='محصولات مرتبط')
    categories = models.ManyToManyField(ProductCategory, blank=True, verbose_name='دسته‌بندی‌های مرتبط')

    def is_valid(self):
        now = timezone.now()
        return self.valid_from <= now <= self.valid_to and (
                self.max_usage is None or self.used_count < self.max_usage
        )

    class Meta:
        verbose_name = 'تخفیف'
        verbose_name_plural = 'تخفیف‌ها'

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        pre_save.connect(cls.validate_discount, sender=cls)

    @classmethod
    def validate_discount(cls, sender, instance, **kwargs):
        if instance.valid_to <= instance.valid_from:
            raise ValidationError("تاریخ پایان تخفیف باید بعد از تاریخ شروع باشد.")


class ProductAttributeType(models.Model):
    name = models.CharField(max_length=100, verbose_name='نوع ویژگی')

    class Meta:
        verbose_name = 'نوع ویژگی'
        verbose_name_plural = 'انواع ویژگی‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attribute_values', verbose_name='محصول', null=True, blank=True)
    type = models.ForeignKey(ProductAttributeType, on_delete=models.CASCADE, verbose_name='نوع ویژگی' , null=True, blank=True)
    value = models.CharField(max_length=100, verbose_name='مقدار ویژگی', null=True, blank=True)

    class Meta:
        verbose_name = 'مقدار ویژگی'
        verbose_name_plural = 'مقادیر ویژگی‌ها'
        ordering = ['type', 'value']
        unique_together = ('product', 'type', 'value')

    def __str__(self):
        return f"  {self.type.name}: {self.value}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants',null=True, blank=True, verbose_name='محصول')
    attributes = models.ManyToManyField(ProductAttribute, blank=True, verbose_name='ویژگی‌ها')
    stock = models.PositiveIntegerField(verbose_name='تعداد موجودی' ,null=True, blank=True,)
    price_override = models.IntegerField(null=True, blank=True, verbose_name='قیمت مخصوص این تنوع')
    discount = models.ForeignKey('Discount', null=True, blank=True, on_delete=models.SET_NULL, related_name='variants')

    class Meta:
        verbose_name = 'تنوع محصول'
        verbose_name_plural = 'تنوع‌های محصول'

    def __str__(self):
        def __str__(self):
            return f" - {', '.join([str(attr) for attr in self.attributes.all()])} - تخفیف: {self.discount.code if self.discount else 'بدون تخفیف'}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='محصول')
    image = models.ImageField(upload_to='products/gallery/%Y/%m/%d/', verbose_name='تصویر')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش')
    alt_text = models.CharField(max_length=125, blank=True, verbose_name='متن جایگزین')

    class Meta:
        ordering = ['order']
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'

class ProductReview(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='محصول')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='امتیاز'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان نقد')
    content = models.TextField(verbose_name='محتوا')
    verified_purchase = models.BooleanField(default=False, verbose_name='خرید تایید شده')

    class Meta:
        unique_together = ('product', 'user')
        verbose_name = 'نقد و بررسی'
        verbose_name_plural = 'نقد و بررسی‌ها'


class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views', verbose_name='محصول')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='کاربر')
    ip_address = models.GenericIPAddressField(verbose_name='آدرس IP')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    session_key = models.CharField(max_length=40, blank=True, verbose_name='کلید جلسه')

    class Meta:
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['product', 'timestamp']),
        ]
        verbose_name = 'بازدید محصول'
        verbose_name_plural = 'بازدیدهای محصول'

class Wishlist(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist'  # Correct ✅
    )
    products = models.ManyToManyField(
        Product,
        related_name='wishlisted_by',  # Fixed: removed space ❌ -> ✅
        blank=True
    )

    def count(self):
        return self.products.count()

    def contains_product(self, product):
        return self.products.filter(pk=product.pk).exists()

    class Meta:
        verbose_name = 'لیست علاقه‌مندی‌ها'
        verbose_name_plural = 'لیست‌های علاقه‌مندی'
        ordering = ['-updated_at']

    def __str__(self):
        return f"لیست علاقه‌مندی های {self.user.username}"

class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_variant_prices(self):
        return self.annotate(
            min_variant_price=Min('variants__price_modifier') + F('price'),
            max_variant_price=Max('variants__price_modifier') + F('price')
        )

class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db).active()

class ProductDescription(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='descriptions')
    Image = models.ImageField(upload_to='products/main/%Y/%m/%d/', null=True, blank=True ,verbose_name='تصویر برای هر متن ',)
    title_description = models.CharField(max_length=50, db_index=True, verbose_name='سر تیتر توضیحات کامل ', blank=True, null=True)
    description = models.TextField(verbose_name='توضیحات کامل', null=True, blank=True)

    def __str__(self):
        return self.title_description or "توضیح بدون عنوان"

    class Meta:
        verbose_name = 'توضیحات محصول'
        verbose_name_plural = 'توضیحات محصول'




