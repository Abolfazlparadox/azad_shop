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
    UserCartView,
)
from .views import order_invoice_pdf


urlpatterns = [
    path('', UserCartView.as_view(), name='user_cart_page'),
    path('add-to-cart/', views.AddProductToCartView.as_view(), name='add_product_to_cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('change-cart-detail/', views.change_cart_detail, name='change_cart_detail'),
    path('payment-result/', views.PaymentResultView.as_view(), name='payment_result_page'),

    path('export_pdf/<int:order_id>/', views.export_pdf, name='export_pdf'),
    path('orders/<int:order_id>/invoice/', order_invoice_pdf, name='order_invoice_pdf'),

]
