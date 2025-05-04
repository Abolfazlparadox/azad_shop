from django.views.generic import  DetailView,ListView
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Product, ProductCategory, ProductReview, ProductView, ProductImage, ProductVariant,Wishlist
from decimal import Decimal, DecimalException
from django.core.exceptions import ValidationError
from django.db.models import Q, Max, F, Min, Avg, Prefetch
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from product.models import University  # if needed

class ProductBaseView:
    """Base view with common functionality."""

    def get_price_range(self):
        """Get min/max prices from database with caching."""
        cache_key = 'product_price_range'
        price_range = cache.get(cache_key)
        if not price_range:
            price_range = Product.objects.aggregate(
                max_price=Max('price'),
                min_price=Min('price')
            )
            cache.set(cache_key, price_range, 60 * 60)
        return price_range

    def get_max_available_price(self):
        """Get highest available product price."""
        cache_key = 'max_product_price'
        max_price = cache.get(cache_key)
        if not max_price:
            max_price = Product.objects.aggregate(
                max_price=Max('price')
            )['max_price'] or Decimal('1000000')
            cache.set(cache_key, max_price, 60 * 60)
        return max_price

class ProductListView(ProductBaseView, ListView):
    model = Product
    template_name = 'product/product-list.html'
    context_object_name = 'products'
    paginate_by = 12
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset().select_related('brand').filter(is_active=True)
        qs = qs.prefetch_related(
            Prefetch('categories', queryset=ProductCategory.objects.only('title', 'slug')),
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
            Prefetch('variants', queryset=ProductVariant.objects.only('color', 'size', 'price_modifier'))
        )

        # --- Search ---
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(title__icontains=search)

        # --- Price filtering ---
        try:
            raw_min = self.request.GET.get('min_price')
            raw_max = self.request.GET.get('max_price')
            min_price = Decimal(raw_min) if raw_min else Decimal(0)
            max_price = Decimal(raw_max) if raw_max else self.get_max_available_price()
            if min_price < 0 or max_price < 0:
                raise ValidationError("Prices cannot be negative")
            if min_price > max_price:
                raise ValidationError("Minimum price cannot exceed maximum price")
            qs = qs.filter(price__gte=min_price, price__lte=max_price)
        except (ValueError, TypeError, ValidationError, DecimalException) as e:
            messages.warning(self.request, f"Invalid price range: {e}")

        # --- Category filtering ---
        categories = self.request.GET.getlist('category')
        if categories:
            qs = qs.filter(categories__slug__in=categories)

        # --- Rating filtering ---
        ratings = self.request.GET.getlist('rating')
        if ratings:
            try:
                min_rating = min(map(int, ratings))
                qs = qs.annotate(avg_rating=Avg('reviews__rating')) \
                       .filter(avg_rating__gte=min_rating)
            except Exception as ex:
                messages.warning(self.request, f"Rating filter error: {ex}")

        # --- Discount filtering ---
        discounts = self.request.GET.getlist('discount')
        if discounts:
            try:
                threshold = max(map(int, discounts))
                qs = qs.annotate(
                    discount_pct=F('old_price') - F('price')
                ).filter(discount_pct__gt=0)
            except Exception as ex:
                messages.warning(self.request, f"Discount filter error: {ex}")

        # --- Weight filtering ---
        weights = self.request.GET.getlist('weight')
        if weights:
            try:
                w_vals = [Decimal(w) for w in weights if w.replace('.', '', 1).isdigit()]
                qs = qs.filter(weight__in=w_vals)
            except Exception as ex:
                messages.warning(self.request, f"Weight filter error: {ex}")

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        total = qs.count()
        discounted = qs.filter(old_price__isnull=False, price__lt=F('old_price')).count()
        non_discounted = total - discounted

        price_range = self.get_price_range()
        now = timezone.now()

        ctx.update({
            'products': qs,
            'discounted_products_count': discounted,
            'non_discounted_products_count': non_discounted,
            'price_range': price_range,
            'all_categories': ProductCategory.objects.all(),
            'discount_options': [5, 10, 15, 25],
            'weight_options': ['0.4', '0.5', '0.7', '1'],
            'current_search': self.request.GET.get('search', ''),
            'current_category': self.request.GET.getlist('category'),
            'current_rating': self.request.GET.getlist('rating'),
            'current_discount': self.request.GET.getlist('discount'),
            'current_weight': self.request.GET.getlist('weight'),
            'now': now,
            'banner': {
                'image': 'images/shop/1.jpg',
                'title': 'میوه‌ها و سبزیجات سالم، مغذی و خوش‌طعم',
                'discount': 'تخفیف تا 50٪'
            }
        })
        return ctx

class ProductDetailView(ProductBaseView, DetailView):
    model = Product
    template_name = 'product/product-detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('brand').prefetch_related(
            'images',
            'categories',
            Prefetch('reviews', queryset=ProductReview.objects.select_related('user'))
        ).filter(is_active=True)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        # Track product view
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

        # Calculate discount
        discount = 0
        if product.old_price and product.old_price > product.price:
            discount = round((product.old_price - product.price) / product.old_price * 100)

        # Get review stats
        reviews = product.reviews.all()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        # Get related products (optimized)
        related_products = Product.objects.filter(
            categories__in=product.categories.all()
        ).exclude(pk=product.pk).distinct()[:4]

        context.update({
            'discount_percentage': discount,
            'avg_rating': avg_rating,
            'review_count': reviews.count(),
            'related_products': related_products,
            'product_info': {
                'categories': [c.title for c in product.categories.all()],
                'sku': product.sku,
                'stock': product.stock
            }
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