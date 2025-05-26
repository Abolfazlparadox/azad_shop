from cart.models import Cart, CartDetail
from .models import SiteSetting, FooterLinkBox
from django.core.cache import cache
from iranian_cities.models import Province
from product.models import ProductCategory

def site_settings(request):
    # Retrieve the main site settings from cache or database
    site_settings_1 = cache.get('main_site_settings')
    if site_settings_1 is None:
        site_settings_1 = SiteSetting.objects.filter(is_main_setting=True).first()
        cache.set('main_site_settings', site_settings_1, 60 * 60)  # cache for 1 hour

    # Retrieve footer link boxes from cache or database
    footer_link_boxes = cache.get('footer_link_boxes')
    if footer_link_boxes is None:
        footer_link_boxes = FooterLinkBox.objects.prefetch_related('footerlink_set').all()
        cache.set('footer_link_boxes', footer_link_boxes, 60 * 60)

    # Retrieve social media links
    # Here we assume the social links belong to a FooterLinkBox whose title contains "اجتماعی"
    social_links = cache.get('social_links')
    if social_links is None:
        social_box = FooterLinkBox.objects.filter(title__icontains="اجتماعی").first()
        if social_box:
            social_links = social_box.footerlink_set.all()
        else:
            social_links = []  # Fallback: an empty list if no box found
        cache.set('social_links', social_links, 60 * 60)

    return {
        'site_settings': site_settings_1,
        'footer_link_boxes': footer_link_boxes,
        'social_links': social_links,
    }
def location_data(request):
    provinces = cache.get('all_provinces')
    if provinces is None:
        provinces = Province.objects.all()
        cache.set('all_provinces', provinces, 60 * 60)
    return {'provinces': provinces}

def user_city(request):
    """
    Add the authenticated user's city name (in Persian) to the context.
    """
    city_name = ''
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        # Assuming `user.city.name` is already the Persian name
        city = getattr(user, 'city', None)
        if city:
            city_name = city.name
    return {'user_city': city_name}

def main_categories_processor(request):
    main_categories = ProductCategory.objects.filter(is_active=True, parent=None).prefetch_related('children')
    return {
        'main_categories': main_categories
    }








def cart_context_processor(request):
    cart_items = []
    total_price = 0

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_items = CartDetail.objects.filter(cart=cart)
            total_price = sum(item.get_total_price() for item in cart_items)

    return {
        'cart_items': cart_items,
        'total_price': total_price,
    }
