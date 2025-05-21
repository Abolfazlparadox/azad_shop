from django.db import models
from django.utils import timezone
from account.models import User
from product.models import Product, ProductVariant, ProductCategory , Discount
from django.core.exceptions import ValidationError
from account.models import Address


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    is_paid = models.BooleanField(null=True, blank=True, default=False , verbose_name='نهایی شده / نشده')
    payment_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    created_at = models.DateTimeField(auto_now_add=True , null=True, blank=True, verbose_name='تاریخ ایجاد سبد خرید')
    updated_at = models.DateTimeField(auto_now=True ,null=True, blank=True,verbose_name='تاریخ تغیر در سبد خرید' )
    def __str__(self):
        return str(self.user)

    def calculate_total_price(self):
        total_amount = 0
        for cart_detail in self.cartdetail_set.all():
            total_amount += cart_detail.get_total_price()
        return total_amount

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید کاربران'

class CartDetail(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name='سبد خرید')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, verbose_name='مشخصات محصول')
    final_price = models.PositiveIntegerField( null=True, blank=True, verbose_name='قیمت نهایی تکی محصول')
    count = models.PositiveIntegerField(verbose_name='تعداد')
    created_at = models.DateTimeField(auto_now_add=True , null=True, blank=True, verbose_name='تاریخ ایجاد جزئیات سبد خرید')
    updated_at = models.DateTimeField(auto_now=True , null=True, blank=True, verbose_name='تاریخ تغییر در جزئیات سبد خرید')
    def __str__(self):
        return f"{self.product} x {self.count}"

    def clean(self):
        # اطمینان از همخوانی محصول و تنوع
        if self.variant and self.variant.product != self.product:
            raise ValidationError("تنوع انتخاب شده با محصول همخوانی ندارد.")
        if not self.variant:
            raise ValidationError("باید یک تنوع محصول (variant) انتخاب شود تا قیمت قابل محاسبه باشد.")
        if self.count <= 0:
            raise ValidationError("تعداد باید بیشتر از صفر باشد.")

    def get_unit_price(self):
        # اگر final_price از قبل محاسبه شده بود استفاده کن
        if self.final_price is not None:
            return self.final_price

        # قیمت نهایی را از variant می‌گیریم
        if self.variant:
            price = self.variant.final_price()
            if price is not None:
                return price

        # اگر هیچ قیمت معتبری نبود، صفر برگردان
        return 0

    def get_total_price(self):
        return self.count * self.get_unit_price()

    @property
    def discount_amount(self):
        if self.variant and self.variant.price:
            original_price = self.variant.price or 0
            discounted_price = self.variant.final_price() or 0
            return max(0, original_price - int(discounted_price))
        return 0

    @property
    def total_discount(self):
        return self.discount_amount * self.count

    def save(self, *args, **kwargs):
        # قبل از ذخیره حتما اعتبارسنجی انجام شود
        self.full_clean()

        if self.final_price is None:
            self.final_price = self.get_unit_price()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'جزئیات سبد خرید'
        verbose_name_plural = 'لیست جزئیات سبدهای خرید'

class Order(models.Model):
    STATUS_PENDING = 'pending'          # در حال انتظار تایید
    STATUS_CONFIRMED = 'confirmed'      # تایید شده
    STATUS_SHIPPING = 'shipping'        # در حال ارسال به پست
    STATUS_DELIVERING = 'delivering'    # در حال ارسال پست به مقصد

    STATUS_CHOICES = [
        (STATUS_PENDING, 'در حال انتظار تایید'),
        (STATUS_CONFIRMED, 'تایید شده'),
        (STATUS_SHIPPING, 'در حال ارسال به پست'),
        (STATUS_DELIVERING, 'در حال ارسال پست به مقصد'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="کاربر")
    created_at = models.DateTimeField(auto_now_add=True , null=True, blank=True, verbose_name='تاریخ ثبت سفارش ')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='وضعیت سفارش'
    )
    total_price = models.PositiveIntegerField(verbose_name="مبلغ کل")
    shipping_cost = models.PositiveIntegerField(default=70000)
    final_price = models.PositiveIntegerField(verbose_name="مبلغ نهایی پرداختی")
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"سفارش #{self.id} - کاربر: {self.user.username} - وضعیت: {self.get_status_display()}"


    class Meta:
        verbose_name = ' سفارش '
        verbose_name_plural = 'لیست سفارش ها'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    count = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product} x {self.count}"

    class Meta:
        verbose_name = ' جزئیات سفارش  '
        verbose_name_plural = 'لیست جزئیات سفارش ها'