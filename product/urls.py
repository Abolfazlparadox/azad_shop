from django.urls import path, register_converter
from django.conf.urls.static import static
from django.conf import settings
from utility.converters import UnicodeSlugConverter
from .views import (
    ProductListView,
    ProductDetailView,
    compare_products,
    toggle_wishlist,

)


register_converter(UnicodeSlugConverter, 'uslug')

app_name = 'product'  # Add namespace for reverse URL lookups

urlpatterns = [
    # Product listing URLs
    path('', ProductListView.as_view(), name='list'),

    path('category/<uslug:category_slug>/',
         ProductListView.as_view(), name='category-list'),
    path('brand/<uslug:brand_slug>/',
         ProductListView.as_view(), name='brand-list'),

    path('product/<uslug:slug>/',
         ProductDetailView.as_view(),
         name='product-detail'),  # This name matches the reverse() call

    # Wishlist functionality
    path('wishlist/toggle/<int:product_id>/',
         toggle_wishlist, name='toggle-wishlist'),

    # Product comparison
    path('compare/',
         compare_products, name='compare'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)