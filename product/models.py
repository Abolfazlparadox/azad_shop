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
from colorfield.fields import ColorField
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
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='وزن (گرم)')
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

    def __str__(self):
        return f"کد تخفیف: {self.code}, نوع: {self.discount_type}, مقدار: {self.amount} تومان"
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
    type = models.ForeignKey(ProductAttributeType, on_delete=models.CASCADE, verbose_name='نوع ویژگی', null=True, blank=True)
    value = models.CharField(max_length=100, verbose_name='مقدار ویژگی', null=True, blank=True)
    COLOR_CHOICES = [
        ("#5c5ccd", "جگری"),
        ("#8080f0", "بژ تیره"),
        ("#7280fa", "حناییِ روشن"),
        ("#7a96e9", "قهوه‌ایِ حنایی"),
        ("#7aa0ff", "کرم نارنجی"),
        ("#0000ff", "قرمز"),
        ("#3c14dc", "زرشکی"),
        ("#2222b2", "شرابی"),
        ("#00008b", "عنابی تند"),
        ("#cbc0ff", "صورتی"),
        ("#c1b6ff", "صورتی پررنگ"),
        ("#9370db", "شرابی روشن"),
        ("#b469ff", "سرخابی"),
        ("#9314ff", "شفقی"),
        ("#8515c7", "ارغوانی"),
        ("#00a5ff", "نارنجی"),
        ("#008cff", "نارنجی سیر"),
        ("#507fff", "نارنجی پررنگ"),
        ("#4763ff", "قرمز گوجه‌ای"),
        ("#0045ff", "قرمز-نارنجی"),
        ("#e0ffff", "شیری"),
        ("#cdfaff", "شیرشکری"),
        ("#d2fafa", "لیمویی روشن"),
        ("#d5efff", "هلویی روشن"),
        ("#b5e4ff", "هلویی"),
        ("#b9daff", "هلویی پررنگ"),
        ("#aae8ee", "نخودی"),
        ("#83e6f0", "خاکی"),
        ("#00ffff", "زرد"),
        ("#00d7ff", "کهربایی باز"),
        ("#6bb7bd", "ماشی"),
        ("#2fffad", "مغزپسته‌ای"),
        ("#00ff7f", "سبز روشن"),
        ("#00fc7c", "مغزپسته‌ای پررنگ"),
        ("#00ff00", "مغزپسته‌ای"),
        ("#98fb98", "سبز کمرنگ"),
        ("#90ee90", "سبز کدر"),
        ("#9afa00", "یشمی سیر"),
        ("#7fff00", "یشمی کمرنگ"),
        ("#32cd9a", "سبز لجنی"),
        ("#32cd32", "سبز چمنی"),
        ("#71b33c", "خزه‌ای"),
        ("#578b2e", "خزه‌ای پررنگ"),
        ("#228b22", "شویدی"),
        ("#008000", "سبز"),
        ("#238e6b", "سبز ارتشی"),
        ("#008080", "زیتونی"),
        ("#2f6b55", "زیتونی سیر"),
        ("#006400", "سبز آووکادو"),
        ("#aacd66", "سبز دریایی"),
        ("#8fbc8f", "سبز دریایی تیره"),
        ("#aab220", "سبز کبریتی روشن"),
        ("#8b8b00", "سبز کبریتی تیره"),
        ("#808000", "سبز دودی"),
        ("#ffff00", "فیروزه‌ای"),
        ("#ffffe0", "آبی آسمانی"),
        ("#eeeeaf", "فیروزه‌ای کدر"),
        ("#d4ff7f", "یشمی"),
        ("#d0e040", "سبز دریایی روشن"),
        ("#ccd148", "فیروزه‌ای تیره"),
        ("#d1ce00", "فیروزه‌ای سیر"),
        ("#e6e0b0", "آبی کبریتی روشن"),
        ("#dec4b0", "بنفش مایل به آبی"),
        ("#e6d8ad", "آبی کبریتی"),
        ("#ebce87", "آبی آسمانی سیر"),
        ("#face87", "آبی روشن"),
        ("#ffbf00", "آبی کمرنگ"),
        ("#ed9564", "آبی کدر"),
        ("#b48246", "نیلی متالیک"),
        ("#a09e5f", "آبی لجنی"),
        ("#ee687b", "آبی متالیک روشن"),
        ("#ff901e", "نیلی"),
        ("#e16941", "فیروزه‌ای فسفری"),
        ("#ff0000", "آبی"),
        ("#cd0000", "آبی سیر"),
        ("#8b0000", "سرمه‌ای"),
        ("#800000", "لاجوردی"),
        ("#701919", "آبی نفتی"),
        ("#fae6e6", "نیلی کمرنگ"),
        ("#d8bfd8", "بادمجانی روشن"),
        ("#dda0dd", "بنفش کدر"),
        ("#ee82ee", "بنفش روشن"),
        ("#ff00ff", "سرخابی"),
        ("#d670da", "ارکیده"),
        ("#d355ba", "ارکیده سیر"),
        ("#db7093", "آبی بنفش"),
        ("#cd5a6a", "آبی فولادی"),
        ("#e22b8a", "آبی-بنفش سیر"),
        ("#d30094", "بنفش باز"),
        ("#cc3299", "ارکیده بنفش"),
        ("#8b008b", "مخملی"),
        ("#800080", "بنفش"),
        ("#8b3d48", "آبی دودی"),
        ("#82004b", "نیلی سیر"),
        ("#dcf8ff", "کاهی"),
        ("#cdebff", "کاهگلی"),
        ("#c4e4ff", "کرم"),
        ("#addeff", "کرم سیر"),
        ("#bcdef5", "گندمی"),
        ("#87b8de", "خاکی"),
        ("#8cb4d2", "برنزه کدر"),
        ("#8f8fbc", "بادمجانی"),
        ("#60a4f4", "هلویی سیر"),
        ("#20a5da", "خردلی"),
        ("#0b86b8", "ماشی سیر"),
        ("#3f85cd", "بادامی سیر"),
        ("#1e69d2", "عسلی پررنگ"),
        ("#13458b", "کاکائویی"),
        ("#2d52a0", "قهوه‌ای متوسط"),
        ("#2a2aa5", "قهوه‌ای"),
        ("#000080", "آلبالویی"),
        ("#ffffff", "سفید"),
        ("#fafaff", "صورتی محو"),
        ("#f0fff0", "یشمی محو"),
        ("#fafff5", "سفید نعنائی"),
        ("#fffff0", "آبی محو"),
        ("#fff8f0", "نیلی محو"),
        ("#fff8f8", "سفید بنفشه"),
        ("#f5f5f5", "خاکستری محو"),
        ("#eef5ff", "بژ باز"),
        ("#dcf5f5", "هِلی"),
        ("#e6f5fd", "بژ روشن"),
        ("#f0faff", "پوست پیازی"),
        ("#f0ffff", "استخوانی"),
        ("#d7ebfa", "بژ تیره"),
        ("#e6f0fa", "کتانی"),
        ("#f5f0ff", "صورتی مات"),
        ("#e1e4ff", "بژ"),
        ("#dcdcdc", "خاکستری مات"),
        ("#d3d3d3", "نقره‌ای"),
        ("#c0c0c0", "توسی"),
        ("#a9a9a9", "خاکستری سیر"),
        ("#808080", "خاکستری"),
        ("#696969", "دودی"),
        ("#998877", "سربی"),
        ("#908070", "سربی تیره"),
        ("#4f4f2f", "لجنی تیره"),
        ("#000000", "سیاه"),
    ]
    image = models.ImageField(upload_to="images",verbose_name='رنگ به صورت عکس',help_text='اگر یه رنگ خاص دارید که داخل رنگ های اشافه شده نبود یه عکس از یه بخش از اون محصول رو آپلود کنید و اسم رنگ رو داخل فیلد مقدار ویژگی وارد کنید سپس گزینه ذخبره رو بزنید دوباره وارد همون رنگی که عکس رو وارد کردید بشید و چک کنید که رنگ مورد نظر شما با رنگ انتخابی شبیه هم هستند', null=True, blank=True)

    color = ColorField(
        image_field="image",
        samples=COLOR_CHOICES,
        help_text='فقط اگه مقدار ویژگی را میخواستید رنگ بزارید اول از این قسمت استفاده کنید',
        verbose_name='رنگ به صورت استاتیک'
    )

    class Meta:
        verbose_name = 'مقدار ویژگی'
        verbose_name_plural = 'مقادیر ویژگی‌ها'
        ordering = ['type', 'value','id']
        unique_together = ( 'type', 'value')

    def __str__(self):
        return f"{self.type.name}: {self.value}"

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




