from django.views.generic import  DetailView,ListView
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Product, ProductCategory, ProductReview, ProductView, ProductImage, ProductVariant,Wishlist ,ProductDescription
from decimal import Decimal, DecimalException
from django.core.exceptions import ValidationError
from django.db.models import Q, Max, F, Min, Avg, Prefetch
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.template.loader import render_to_string
from collections import defaultdict
from django.db.models import Prefetch
from django.utils import timezone
from django.views.generic import ListView
from product.models import University  # if needed

class ProductBaseView:
    """Base view with common functionality."""

    def get_price_range(self):
        """Get min/max prices from ProductVariant with caching."""
        cache_key = 'product_price_range'
        price_range = cache.get(cache_key)
        if not price_range:
            price_range = ProductVariant.objects.aggregate(
                max_price=Max('price_override'),
                min_price=Min('price_override')
            )
            cache.set(cache_key, price_range, 60 * 60)
        return price_range

    def get_max_available_price(self):
        """Get highest available product variant price."""
        cache_key = 'max_product_variant_price'
        max_price = cache.get(cache_key)
        if not max_price:
            max_price = ProductVariant.objects.aggregate(
                max_price=Max('price_override')
            )['max_price'] or Decimal('1000000')  # Default to a high value if no variants found
            cache.set(cache_key, max_price, 60 * 60)
        return max_price




class ProductListView(ListView):
    model = Product
    template_name = 'product/product-list.html'
    context_object_name = 'products'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        print("شروع دریافت queryset...")  # پرینت برای شروع گرفتن داده‌ها
        qs = super().get_queryset().filter(is_active=True)
        qs = qs.select_related('brand', 'university') \
            .prefetch_related(
                Prefetch('categories', queryset=ProductCategory.objects.only('title', 'slug')),
                Prefetch('images', queryset=ProductImage.objects.order_by('order')),
                Prefetch('variants', queryset=ProductVariant.objects.select_related('discount')
                         .prefetch_related('attributes'))
            )
        print(f"تعداد محصولات یافت‌شده: {qs.count()}")  # پرینت تعداد محصولات یافت‌شده
        return qs

    def get_context_data(self, **kwargs):
        print("شروع پردازش context...")  # پرینت برای شروع پردازش context
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        querydict = self.request.GET.copy()

        if 'page' in querydict:
            querydict.pop('page')

        qs = self.get_queryset()

        sizes = set()
        colors = set()
        product_variant_map = {}

        # پرینت برای شروع پردازش محصولات
        print("شروع پردازش محصولات...")

        for product in qs:
            print(f"در حال پردازش محصول: {product.title}")  # پرینت نام هر محصول
            color_to_sizes = defaultdict(set)
            size_to_colors = defaultdict(set)
            variants_list = []

            for variant in product.variants.all():
                print(f"  در حال پردازش واریانت: {variant.pk}")
                color = None
                sizes_in_variant = []

                for attr in variant.attributes.all():
                    if attr.type.name == 'رنگ' and not color:
                        color = attr.color
                        colors.add(color)
                        print(f"    رنگ: {color}")
                    elif attr.type.name == 'سایز':
                        size = attr.value
                        sizes.add(size)
                        sizes_in_variant.append(size)
                        print(f"    سایز: {size}")

                # نگاشت‌ها براساس وجود رنگ یا سایز ساخته می‌شن
                if color:
                    if sizes_in_variant:
                        for size in sizes_in_variant:
                            color_to_sizes[str(color)].add(size)
                            size_to_colors[size].add(str(color))
                    else:
                        # اگر فقط رنگ وجود داشت
                        color_to_sizes[str(color)].add(None)

                if sizes_in_variant and not color:
                    for size in sizes_in_variant:
                        size_to_colors[size].add(None)

                variants_list.append({
                    'variant_id': variant.pk,
                    'color': str(color) if color else None,
                    'sizes': sizes_in_variant,
                    'price': variant.price_override or variant.product.price,
                    'stock': variant.stock,
                    'discount': variant.discount.amount if variant.discount else None,
                })

            color_to_sizes = {k: list(v) for k, v in color_to_sizes.items()}
            size_to_colors = {k: list(v) for k, v in size_to_colors.items()}

            # پرینت اطلاعات مربوط به رنگ‌ها و سایزها
            print(f"    رنگ‌ها به سایزها: {color_to_sizes}")
            print(f"    سایزها به رنگ‌ها: {size_to_colors}")

            product_variant_map[product.pk] = {
                'color_to_sizes': color_to_sizes,
                'size_to_colors': size_to_colors,
                'variants': variants_list,
            }

        # پرینت اطلاعات نهایی
        print(f"رنگ‌ها: {colors}")
        print(f"سایزها: {sizes}")
        print(f"مجموعه واریانت‌ها: {product_variant_map}")

        context.update({
            'now': now,
            'query_string': querydict.urlencode(),
            'sizes': sizes,
            'colors': list(colors),
            'product_variant_map': product_variant_map,  # ✅ کافی است فقط همین را داشته باشید
        })

        return context




class ProductDetailView(ProductBaseView, DetailView):
    model = Product
    template_name = 'product/product-detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('brand').prefetch_related(
            'images',
            'categories',
            Prefetch('reviews', queryset=ProductReview.objects.select_related('user')),
            'tags',  # اگر استفاده شده
            Prefetch('descriptions', queryset=ProductDescription.objects.all())  # افزودن توضیحات
        ).filter(is_active=True)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        # Ensure session exists
        if not request.session.session_key:
            request.session.save()

        # Track product view for anonymous users
        if not request.user.is_authenticated:
            ProductView.objects.create(
                product=self.object,
                ip_address=self.get_client_ip(request),
                session_key=request.session.session_key
            )

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # محاسبه درصد تخفیف
        discount = 0
        if product.old_price and product.old_price > product.price:
            discount = round((product.old_price - product.price) / product.old_price * 100)

        # اطلاعات مربوط به بازخوردها
        reviews = product.reviews.all()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        # محصولات مشابه
        related_products = Product.objects.filter(
            categories__in=product.categories.all()
        ).exclude(pk=product.pk).distinct()[:4]

        # اضافه کردن توضیحات به context
        descriptions = product.descriptions.all()

        context.update({
            'discount_percentage': discount,
            'avg_rating': avg_rating,
            'review_count': reviews.count(),
            'related_products': related_products,
            'product_info': {
                'type': getattr(product, 'type', '---'),
                'sku': product.sku,
                'created_at': product.created_at,
                'stock': product.stock,
                'tags': ', '.join(tag.name for tag in product.tags.all()) if hasattr(product, 'tags') else '',
                'categories': [c.title for c in product.categories.all()]
            },
            'descriptions': descriptions  # توضیحات رو به context اضافه می‌کنیم
        })
        return context





@require_POST
@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    if product in wishlist.products.all():
        wishlist.products.remove(product)
        added = False
    else:
        wishlist.products.add(product)
        added = True

    return JsonResponse({'added': added, 'count': wishlist.products.count()})

def compare_products(request):
    product_ids = request.GET.getlist('products')
    products = Product.objects.filter(pk__in=product_ids).prefetch_related(
        'categories', 'brand', 'variants'
    )[:4]  # Limit comparison to 4 products

    # Get common features for comparison
    features = {}
    for product in products:
        for variant in product.variants.all():
            for field in ['color', 'size', 'material']:
                features.setdefault(field, set()).add(getattr(variant, field))

    return render(request, 'product/product-compare.html', {
        'products': products,
        'features': {k: list(v) for k, v in features.items()}
    })


