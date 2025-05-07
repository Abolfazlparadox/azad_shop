from django.db import models
from django.utils import timezone
from account.models import User
from product.models import Product, ProductVariant, ProductCategory , Discount


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    is_paid = models.BooleanField(null=True, blank=True, verbose_name='نهایی شده / نشده')
    payment_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پرداخت')

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
    Variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, verbose_name='مشخصات محصول')
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='قیمت نهایی تکی محصول')
    count = models.PositiveIntegerField(verbose_name='تعداد')

    def __str__(self):
        return f"{self.product} x {self.count}"

    def get_unit_price(self):
        if self.final_price is not None:
            return self.final_price

        now = timezone.now()
        discount = Discount.objects.filter(
            valid_from__lte=now,
            valid_to__gte=now,
        ).filter(
            models.Q(products=self.product) | models.Q(categories__in=self.product.categories.all())
        ).order_by('-amount').first()

        price = self.product.price

        if discount:
            if discount.discount_type == 'percent':
                discount_value = price * discount.amount / 100
                if discount.max_discount:
                    discount_value = min(discount_value, discount.max_discount)
                price -= discount_value
            elif discount.discount_type == 'fixed':
                price = max(price - discount.amount, 0)

        return price

    def get_total_price(self):
        return self.count * self.get_unit_price()

    def save(self, *args, **kwargs):
        # اگر final_price مقدار ندارد، آن را محاسبه کن
        if self.final_price is None:
            self.final_price = self.get_unit_price()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'جزئیات سبد خرید'
        verbose_name_plural = 'لیست جزئیات سبدهای خرید'
