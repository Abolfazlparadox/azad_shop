# from django.urls import path
# from . import views
#
# urlpatterns = [
#     path('add-to-cart', views.AddProductToCartView, name='add_product_to_cart'),
#     path('request-payment/', views.RequestPaymentView, name='request_payment'),
#     path('verify-payment/', views.VerifyPaymentView, name='verify_payment')
# ]
from django.urls import path
from . import views
from .views import (
    AddProductToCartView,
    CheckoutView,
    UserCartView
)
urlpatterns = [
    path('', UserCartView.as_view(), name='user_cart_page'),
    path('add-to-cart/', views.AddProductToCartView.as_view(), name='add_product_to_cart'),  # اضافه کردن محصول به سبد خرید
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),  # صفحه تسویه حساب
    # مسیرهای دیگر، مانند پرداخت یا تأیید پرداخت، اگر نیاز دارید، می‌توانید اضافه کنید.
]
