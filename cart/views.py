from django.shortcuts import render, redirect
import time
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
# ----------------------------- Add Product to Cart View -----------------------------
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from .models import Cart, CartDetail, ProductVariant
from .models import Product
from django.utils import timezone

class AddProductToCartView(View):
    def get(self, request, *args, **kwargs):
        # گرفتن پارامترها از URL
        product_id = request.GET.get('product_id')
        count = request.GET.get('count')

        # بررسی اینکه پارامترها موجود باشند و معتبر باشند
        if product_id is None or count is None:
            return JsonResponse({
                'status': 'error',
                'text': 'پارامترهای ورودی معتبر نیستند.',
                'confirm_button_text': 'مرسی از شما',
                'icon': 'warning'
            })

        try:
            product_id = int(product_id)
            count = int(count)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'text': 'مقدارهای وارد شده معتبر نیستند.',
                'confirm_button_text': 'مرسی از شما',
                'icon': 'warning'
            })

        if count < 1:
            return JsonResponse({
                'status': 'invalid_count',
                'text': 'مقدار وارد شده معتبر نمی باشد',
                'confirm_button_text': 'مرسی از شما',
                'icon': 'warning'
            })

        if request.user.is_authenticated:
            # گرفتن محصول بر اساس product_id
            product = get_object_or_404(Product, id=product_id)

            # سبد خرید کاربر را پیدا کنید یا بسازید
            current_cart, created = Cart.objects.get_or_create(is_paid=False, user=request.user)

            # بررسی اینکه آیا محصول قبلاً در سبد خرید هست
            current_cart_detail = current_cart.cartdetail_set.filter(product=product).first()

            if current_cart_detail:
                # اگر محصول قبلاً موجود بود، تعداد آن را به‌روزرسانی می‌کنیم
                current_cart_detail.count += count
                current_cart_detail.save()
            else:
                # اگر محصول جدید بود، جزئیات سبد خرید جدیدی ایجاد می‌کنیم
                CartDetail.objects.create(cart=current_cart, product=product, count=count)

            return JsonResponse({
                'status': 'success',
                'text': 'محصول مورد نظر با موفقیت به سبد خرید شما اضافه شد',
                'confirm_button_text': 'باشه ممنونم',
                'icon': 'success'
            })
        else:
            return JsonResponse({
                'status': 'not_auth',
                'text': 'برای افزودن محصول به سبد خرید ابتدا می بایست وارد سایت شوید',
                'confirm_button_text': 'ورود به سایت',
                'icon': 'error'
            })





# ----------------------------- Checkout View -----------------------------
class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        current_cart, created = Cart.objects.get_or_create(is_paid=False, user_id=request.user.id)
        cart_details = current_cart.cartdetail_set.all()

        if not cart_details:
            return redirect('user_cart_page')  # اگر سبد خرید خالی بود، هدایت به صفحه سبد خرید

        total_price = current_cart.calculate_total_price()  # محاسبه قیمت کل سبد خرید
        return render(request, 'cart_module/checkout.html', {
            'cart_details': cart_details,
            'total_price': total_price
        })

    def post(self, request, *args, **kwargs):
        current_cart, created = Cart.objects.get_or_create(is_paid=False, user_id=request.user.id)
        current_cart.is_paid = True
        current_cart.payment_date = timezone.now()  # تنظیم تاریخ پرداخت به زمان فعلی
        current_cart.save()

        return render(request, 'cart_module/payment_result.html', {
            'success': 'پرداخت شما با موفقیت ثبت شد، سفارش شما در حال پردازش است.'
        })

class UserCartView(LoginRequiredMixin, TemplateView):
    template_name = 'cart.html'  # مسیر قالب HTML که لیست سبد خرید رو نشون میده

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart, created = Cart.objects.get_or_create(user=self.request.user, is_paid=False)
        context['cart_items'] = cart.cartdetail_set.all()
        context['total_price'] = cart.calculate_total_price() if hasattr(cart, 'calculate_total_price') else 0
        return context