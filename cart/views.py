from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django import forms
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from .models import Cart, CartDetail, Product, ProductVariant , Order , OrderItem
from account.models import Address  # مسیر رو بر اساس پروژه خودت اصلاح کن

from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django.template.loader import get_template
from xhtml2pdf import pisa
import datetime

# ----------------------------- Add Product to Cart View -----------------------------
class AddProductToCartView(View):
    def get(self, request, *args, **kwargs):
        product_id = request.GET.get('product_id')
        variant_id = request.GET.get('variant_id')  # اضافه شده
        count = request.GET.get('count')

        if not all([product_id, variant_id, count]):
            return JsonResponse({
                'status': 'error',
                'text': 'پارامترهای ورودی ناقص هستند.',
                'confirm_button_text': 'باشه',
                'icon': 'warning'
            })

        try:
            product_id = int(product_id)
            variant_id = int(variant_id)
            count = int(count)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'text': 'مقادیر وارد شده معتبر نیستند.',
                'confirm_button_text': 'فهمیدم',
                'icon': 'warning'
            })

        if count < 1:
            return JsonResponse({
                'status': 'invalid_count',
                'text': 'تعداد باید حداقل ۱ باشد.',
                'confirm_button_text': 'باشه',
                'icon': 'warning'
            })

        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'not_auth',
                'text': 'برای افزودن محصول باید وارد شوید.',
                'confirm_button_text': 'ورود',
                'icon': 'error'
            })

        product = get_object_or_404(Product, id=product_id)
        variant = get_object_or_404(ProductVariant, id=variant_id)

        if variant.product_id != product.id:
            return JsonResponse({
                'status': 'error',
                'text': 'تنوع انتخاب شده با محصول همخوانی ندارد.',
                'confirm_button_text': 'باشه',
                'icon': 'error'
            })

        cart, created = Cart.objects.get_or_create(is_paid=False, user=request.user)

        cart_detail = cart.cartdetail_set.filter(product=product, variant=variant).first()

        if cart_detail:
            cart_detail.count += count
            cart_detail.save()
        else:
            CartDetail.objects.create(
                cart=cart,
                product=product,
                variant=variant,
                count=count
            )

        return JsonResponse({
            'status': 'success',
            'text': 'محصول با موفقیت به سبد خرید اضافه شد.',
            'confirm_button_text': 'ممنونم',
            'icon': 'success'
        })


# ----------------------------- Checkout View -----------------------------

class CheckoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        cart, created = Cart.objects.get_or_create(is_paid=False, user=request.user)
        cart_details = cart.cartdetail_set.all()

        if not cart_details:
            return redirect('user_cart_page')

        total_price = sum(item.get_total_price() for item in cart_details)
        total_discount = sum(item.total_discount for item in cart_details)
        shipping_cost = 70000
        final_price = total_price + shipping_cost

        addresses = Address.objects.filter(user=request.user)

        return render(request, 'cart_module/checkout.html', {
            'cart_details': cart_details,
            'total_price': total_price,
            'total_discount': total_discount,
            'shipping_cost': shipping_cost,
            'final_price': final_price,
            'cart': cart,
            'addresses': addresses,
        })

    def post(self, request, *args, **kwargs):
        # بررسی اینکه درخواست از AJAX آمده یا نه
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        # گرفتن آدرس انتخاب شده از فرم (یا از payload POST)
        address_id = request.POST.get('selected_address')
        if not address_id:
            error_msg = 'لطفاً یک آدرس برای ارسال انتخاب کنید.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            else:
                return render(request, 'cart_module/payment_result.html', {'error': error_msg})

        cart = get_object_or_404(Cart, user=request.user, is_paid=False)
        cart_details = cart.cartdetail_set.select_related('variant', 'product').all()

        if not cart_details:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'سبد خرید شما خالی است.'})
            else:
                return redirect('user_cart_page')

        # گرفتن آدرس و اطمینان از تعلق آن به کاربر
        address = get_object_or_404(Address, id=address_id, user=request.user)

        shipping_cost = 70000
        total_price = sum(item.get_total_price() for item in cart_details)
        total_discount = sum(item.total_discount for item in cart_details)
        final_price = total_price + shipping_cost

        with transaction.atomic():
            for item in cart_details:
                if item.variant.stock is None or item.variant.stock < item.count:
                    error_msg = f"موجودی برای «{item.product}» کافی نیست."
                    if is_ajax:
                        return JsonResponse({"success": False, "error": error_msg})
                    else:
                        return render(request, 'cart_module/payment_result.html', {'error': error_msg})
                item.variant.stock -= item.count
                item.variant.save()

            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                shipping_cost=shipping_cost,
                final_price=final_price,
                address=address
            )

            for item in cart_details:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    count=item.count,
                    unit_price=item.get_unit_price(),
                    total_price=item.get_total_price()
                )

            cart.is_paid = True
            cart.payment_date = timezone.now()
            cart.save()
            cart_details.delete()
        if is_ajax:
            return JsonResponse({
                'success': True,
                'redirect_url': '/cart/payment-result/'  # یا هر آدرس دلخواه
            })
        else:
            return redirect('payment_result_page')  # اگر فرم معمولی بود







class PaymentResultView(LoginRequiredMixin, TemplateView):
    template_name = 'cart_module/payment_result.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order_id = self.request.GET.get('order_id')
        if not order_id:
            order = self.request.user.order_set.order_by('-created_at').first()
        else:
            order = get_object_or_404(Order, id=order_id, user=self.request.user)

        order_items = order.items.select_related('variant').all()

        # محاسبه مجموع تخفیف
        total_discount = 0
        for item in order_items:
            original_price = item.variant.price if item.variant and item.variant.price else 0
            discount_per_unit = max(0, original_price - item.unit_price)
            total_discount += discount_per_unit * item.count

        context['order'] = order
        context['order_items'] = order_items
        context['total_discount'] = total_discount
        return context











#----------- User Cart Page View -----------------------------


class UserCartView(LoginRequiredMixin, TemplateView):
    template_name = 'cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart, created = Cart.objects.get_or_create(user=self.request.user, is_paid=False)
        cart_items = cart.cartdetail_set.all()
        context['cart_items'] = cart_items
        context['total_price'] = sum([item.get_total_price() for item in cart_items])
        return context


# ----------------------------- Remove from Cart -----------------------------
def remove_from_cart(request, pk):
    item = get_object_or_404(CartDetail, pk=pk)
    if item.cart.user == request.user:
        item.delete()
    return redirect('user_cart_page')


# ----------------------------- Change Cart Detail (increase/decrease count) -----------------------------
@login_required
def change_cart_detail(request):
    if request.method == "GET":
        cart_detail_id = request.GET.get('detail_id')
        state = request.GET.get('state')

        try:
            cart_detail = CartDetail.objects.get(id=cart_detail_id)

            # بررسی مالکیت کاربر روی سبد خرید
            if cart_detail.cart.user != request.user:
                return JsonResponse({'status': 'unauthorized'})

            # افزایش یا کاهش تعداد
            if state == 'increase':
                cart_detail.count += 1
                cart_detail.save()

            elif state == 'decrease':
                if cart_detail.count > 1:
                    cart_detail.count -= 1
                    cart_detail.save()
                else:
                    # حداقل تعداد ۱ است
                    return JsonResponse({
                        'status': 'invalid_count',
                        'message': 'حداقل تعداد ۱ است.',
                        'count': cart_detail.count,
                        'total_price': cart_detail.get_total_price(),
                        'total_cart_price': sum([item.get_total_price() for item in cart_detail.cart.cartdetail_set.all()]),
                        'discount_amount': cart_detail.discount_amount,  # بدون پرانتز
                        'total_discount': cart_detail.total_discount,    # بدون پرانتز
                        'total_cart_discount': sum([item.total_discount for item in cart_detail.cart.cartdetail_set.all()]),
                    })

            cart_details = cart_detail.cart.cartdetail_set.all()

            return JsonResponse({
                'status': 'success',
                'count': cart_detail.count,
                'total_price': cart_detail.get_total_price(),
                'total_cart_price': sum(item.get_total_price() for item in cart_details),
                'discount_amount': cart_detail.discount_amount,  # بدون پرانتز
                'total_discount': cart_detail.total_discount,    # بدون پرانتز
                'total_cart_discount': sum(item.total_discount for item in cart_details),
            })

        except CartDetail.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'موردی یافت نشد'
            })

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import os
from django.conf import settings
from .models import Order
import datetime

import os
import datetime
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from .models import Order  # اگر مدل سفارش در app فعلی باشه

def export_pdf(request, order_id):
    order = Order.objects.get(id=order_id)

    # HTML template rendering
    html_string = render_to_string('order_pdf_user.html', {
        'order': order
    })

    # مسیر فایل‌های فونت و CSS
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Vazir.ttf')
    style_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'rtl.css')

    # ایجاد پاسخ PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=order_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    # استایل‌ها برای weasyprint
    stylesheets = [
        CSS(filename=style_path),
        CSS(string=f"""
            @font-face {{
                font-family: 'Vazir';
                src: url('file:///{font_path.replace(os.sep, "/")}');
            }}
            body {{
                font-family: 'Vazir', sans-serif;
                direction: rtl;
                text-align: right;
                padding: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: center;
            }}
            h3 {{
                text-align: center;
                margin-bottom: 20px;
            }}
        """)
    ]

    # تولید PDF
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(response, stylesheets=stylesheets)

    return response


from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
from .models import Order
from io import BytesIO

def order_invoice_pdf(request, order_id):
    order = Order.objects.get(pk=order_id)
    html_string = render_to_string('order_invoice.html', {'order': order})

    # استفاده از BytesIO برای تولید PDF در حافظه
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)

    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'filename=invoice_order_{order_id}.pdf'
    return response