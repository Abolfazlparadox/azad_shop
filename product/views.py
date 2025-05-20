from django.views.generic import  DetailView,ListView
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Product, ProductCategory, ProductReview, ProductView, ProductImage, ProductVariant,Wishlist ,ProductAttributeType,ProductDescription
from decimal import Decimal, DecimalException
from django.db.models import Q, Max, F, Min, Avg, Prefetch
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from collections import defaultdict
from django.db.models import Prefetch
from django.views.generic import ListView


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
        qs = super().get_queryset().filter(is_active=True).select_related(
            'brand', 'university'
        ).prefetch_related(
            Prefetch('categories', queryset=ProductCategory.objects.only('title', 'slug')),
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
            Prefetch('variants', queryset=ProductVariant.objects.select_related('discount').prefetch_related('attributes'))
        )
        return qs


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product/product-detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        queryset = Product.objects.select_related('brand').prefetch_related(
            'images',
            'categories',
            Prefetch('reviews', queryset=ProductReview.objects.select_related('user')),
            'tags',
            Prefetch('descriptions', queryset=ProductDescription.objects.all())
        ).filter(is_active=True)
        return queryset

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        # اطمینان از وجود session
        if not request.session.session_key:
            request.session.save()

        # ذخیره بازدید برای کاربران ناشناس
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


        # نظرات و امتیاز
        reviews = product.reviews.all()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        # محصولات مرتبط
        related_products = Product.objects.filter(
            categories__in=product.categories.all()
        ).exclude(pk=product.pk).distinct()[:4]

        # ویژگی‌ها و تنوع‌ها
        variants = list(product.variants.prefetch_related('attributes'))
        variant_map = {}
        attribute_map = defaultdict(set)

        # ترتیب ویژگی‌ها از دیتابیس
        ordered_attribute_types = list(ProductAttributeType.objects.order_by('position').values_list('name', flat=True))

        # جمع‌آوری ویژگی‌ها برای فیلترها
        for variant in variants:
            for attr in variant.attributes.all():
                attribute_map[attr.type.name].add(attr)

        # ساخت map یکتا بر اساس ترتیب درست ویژگی‌ها
        for variant in variants:
            attr_dict = {attr.type.name: attr.value for attr in variant.attributes.all()}
            ordered_parts = [f"{attr_type}:{attr_dict[attr_type]}" for attr_type in ordered_attribute_types if
                             attr_type in attr_dict]
            key = ','.join(ordered_parts)

            original_price = variant.price or 0
            final_price = float(variant.final_price() or 0)

            # محاسبه درصد تخفیف
            discount_percent = 0
            if variant.discount and original_price > 0:
                if variant.discount.discount_type == 'percent':
                    discount_percent = variant.discount.amount
                else:
                    # تخفیف مبلغ ثابت → محاسبه درصد تخفیف تقریبی
                    discount_amount = original_price - final_price
                    discount_percent = int((discount_amount * 100) / original_price)

            variant_map[key] = {
                'price': float(variant.final_price() or 0),  # قیمت نهایی (بعد تخفیف)
                'original_price': float(variant.price or 0),  # قیمت اولیه (قبل تخفیف)
                'stock': variant.stock,
                'variant_id': variant.id,
                'discount_percent': 0,
            }
            # محاسبه درصد تخفیف:
            if variant.price and variant.final_price() and variant.price > variant.final_price():
                discount_percent = round(100 * (variant.price - variant.final_price()) / variant.price)
                variant_map[key]['discount_percent'] = discount_percent
            # اضافه به context

        context.update({
            'avg_rating': avg_rating,
            'review_count': reviews.count(),
            'related_products': related_products,
            'product_variant_map': variant_map,
            'product_attribute_map': {
                k: list(v) for k, v in attribute_map.items()
            }
        })

        print("\n✅ Final variant_map:", variant_map)
        print("\n✅ Final attribute_map:", attribute_map)

        return context


# @method_decorator(csrf_exempt, name='dispatch')
# class GetVariantInfoView(View):
#     def post(self, request, *args, **kwargs):
#         product_id = request.POST.get('product_id')
#         attributes = request.POST.getlist('attributes[]')  # مثال: ['قرمز', 'XL', 'کتان']
#
#         try:
#             product = Product.objects.get(pk=product_id)
#         except Product.DoesNotExist:
#             return JsonResponse({'error': 'محصول یافت نشد'}, status=404)
#
#         # پیدا کردن variant دارای همه ویژگی‌ها
#         variants = product.variants.all()
#         for attr_value in attributes:
#             variants = variants.filter(attributes__value=attr_value)
#
#         variant = variants.distinct().first()
#         if variant:
#             return JsonResponse({
#                 'variant_id': variant.id,
#                 'price': variant.final_price(),
#                 'stock': variant.stock,
#                 'discount': variant.discount.amount if variant.discount else 0
#             })
#         else:
#             return JsonResponse({'error': 'ترکیب مورد نظر یافت نشد'}, status=404)


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


