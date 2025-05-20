from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, F
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from admin_auto_filters.filters import AutocompleteFilter
from .models import (Product, ProductCategory, ProductBrand,ProductVariant, ProductImage, ProductReview,Discount, ProductView , ProductDescription)
from .models import ProductAttribute, ProductAttributeType



#
# --------------------------------------------------------------------------
# Inlines
# --------------------------------------------------------------------------
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('attributes','price_override','stock' ,'discount',)

@admin.register(ProductAttributeType)
class ProductAttributeTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    ordering = ['name']


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    class Media:
        js = ('admin/js/admin.js',)
    list_display = ['id', 'type', 'value']
    list_filter = ['type','id']
    search_fields = ['value']
    ordering = ['id']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'get_attributes', 'stock',  ]
    filter_horizontal = ['attributes']

    def get_attributes(self, obj):
        return " / ".join([str(attr) for attr in obj.attributes.all()])
    get_attributes.short_description = 'ویژگی‌ها'

    def final_price(self, instance):
        return instance.product.price + instance.price_modifier
    # def final_price(self, instance):
    #     return instance.product.price + instance.price_modifier
    # final_price.short_description = _('قیمت نهایی')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_preview','image','order','alt_text')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="50"/>', obj.image.url)
        return "-"
    image_preview.short_description = _('پیش‌نمایش')


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------

class CategoryFilter(AutocompleteFilter):
    title = _('دسته‌بندی')
    field_name = 'categories'


class InventoryFilter(admin.SimpleListFilter):
    title = _('موجودی')
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', _('موجود')),
            ('low_stock', _('کم موجود')),
            ('out_of_stock', _('ناموجود')),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'in_stock':
            return queryset.filter(stock__gte=10)
        if val == 'low_stock':
            return queryset.filter(stock__lt=10, stock__gt=0)
        if val == 'out_of_stock':
            return queryset.filter(stock=0)
        return queryset


class UniversityAccessAdmin(admin.ModelAdmin):
    """کلاس پایه برای دسترسی مبتنی بر دانشگاه"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # اگر کاربر سوپر یوزر است همه چیز را ببینید
        if request.user.is_superuser:
            return qs

        membership = request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
        return qs.filter(university=membership.university) if membership else qs.none()

    def save_model(self, request, obj, form, change):
        # تنظیم خودکار دانشگاه هنگام ایجاد رکورد جدید
        if not change and not obj.university:
            membership = request.user.memberships.filter(
                role='OFFI',
                is_confirmed=True
            ).first()
            if membership:
                obj.university = membership.university
        super().save_model(request, obj, form, change)

# --------------------------------------------------------------------------
# ProductCategory & Brand
# --------------------------------------------------------------------------

@admin.register(ProductCategory)
class ProductCategoryAdmin(UniversityAccessAdmin):
    list_display = ('title', 'product_count', 'is_active')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _('تعداد محصولات')



@admin.register(ProductBrand)
class ProductBrandAdmin(UniversityAccessAdmin):
    list_display = ('title', 'logo_preview', 'product_count')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" height="30"/>', obj.logo.url)
        return "-"
    logo_preview.short_description = _('لوگو')

    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = _('تعداد محصولات')


class ProductDescriptionInline(admin.TabularInline):
    model = ProductDescription
    extra = 1
# --------------------------------------------------------------------------
# Product
# --------------------------------------------------------------------------

@admin.register(Product)
class ProductAdmin(UniversityAccessAdmin):
    list_display = (
        'image_preview', 'title',
        'stock_status', 'sku', 'brand', 'category_list'
    )
    list_filter = (
        CategoryFilter, InventoryFilter,
        ('brand', RelatedDropdownFilter),
        ('created_at', admin.DateFieldListFilter),
        ('university', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = ('title', 'sku', 'brand__title', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline, ProductDescriptionInline, ProductVariantInline]
    autocomplete_fields = ['categories', 'tags']
    readonly_fields = ('sku',)
    filter_horizontal = ('categories',)
    raw_id_fields = ('brand',)
    actions = ['restock_products', 'toggle_active']

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'brand', 'categories', 'tags' ,'university')}),
        (_('موجودی'), {'fields': ('weight', 'dimensions')}),
        (_('توضیحات'), {'fields': ('main_image', 'short_description',)}),
        (_('وضعیت'), {'fields': ('is_active', 'is_deleted')}),
    )



    def save_model(self, request, obj, form, change):
        if not change:
            membership = request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
            if membership:
                obj.university = membership.university
        super().save_model(request, obj, form, change)

    def image_preview(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" height="50"/>', obj.main_image.url)
        return "-"
    image_preview.short_description = _('تصویر')

    def category_list(self, obj):
        return ", ".join(c.title for c in obj.categories.all()[:3])
    category_list.short_description = _('دسته‌بندی‌ها')

    def stock_status(self, obj):
        total_stock = sum(variant.stock for variant in obj.variants.all() if variant.stock is not None)
        if total_stock == 0:
            return format_html('<span style="color:red;">{}</span>', _('ناموجود'))
        elif total_stock < 10:
            return format_html('<span style="color:orange;">{}</span>', _('کم موجود'))
        return format_html('<span style="color:green;">{}</span>', _('موجود'))
    stock_status.short_description = _('وضعیت موجودی')

    @admin.action(description=_("افزایش موجودی +100"))
    def restock_products(self, request, queryset):
        for product in queryset:
            for variant in product.variants.all():
                if variant.stock is not None:
                    variant.stock += 100
                    variant.save()
        self.message_user(request, _('موجودی تنوع‌های محصولات انتخابی افزایش یافت.'))

    @admin.action(description=_("تغییر وضعیت فعال/غیرفعال"))
    def toggle_active(self, request, queryset):
        for p in queryset:
            p.is_active = not p.is_active
            p.save()
        self.message_user(request, _('وضعیت محصولات تغییر یافت.'))

# --------------------------------------------------------------------------
# Reviews, Discounts, Views
# --------------------------------------------------------------------------

@admin.register(ProductReview)
class ProductReviewAdmin(UniversityAccessAdmin):
    list_display = ('product', 'user', 'rating', 'verified_purchase', 'created_at')
    list_filter = ('rating', 'verified_purchase', 'created_at')
    raw_id_fields = ('product', 'user')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('product__title', 'user__username')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        membership = request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
        return qs.filter(product__university=membership.university) if membership else qs.none()


@admin.register(Discount)
# class DiscountAdmin(UniversityAccessAdmin):
class DiscountAdmin(admin.ModelAdmin):  # ✅ مشکل حل می‌شود
    list_display = ('code', 'discount_type', 'amount', 'valid_status', 'usage_status')
    list_filter = ('discount_type', 'valid_from', 'valid_to')
    filter_horizontal = ('products', 'categories')
    search_fields = ('code', 'description')
    date_hierarchy = 'valid_from'
    actions = ['validate_discounts']

    def valid_status(self, obj):
        now = timezone.now()
        if now < obj.valid_from:
            return _('آینده')
        if obj.valid_from <= now <= obj.valid_to:
            return _('فعال')
        return _('منقضی')
    valid_status.short_description = _('وضعیت')

    def usage_status(self, obj):
        if obj.max_usage:
            return f"{obj.used_count}/{obj.max_usage}"
        return _('نامحدود')
    usage_status.short_description = _('استفاده')

    @admin.action(description=_("بررسی اعتبار"))
    def validate_discounts(self, request, queryset):
        invalid = [d.code for d in queryset if not d.is_valid()]
        if invalid:
            self.message_user(request, _('کدهای نامعتبر: ') + ", ".join(invalid), level='ERROR')
        else:
            self.message_user(request, _('همه کدهای انتخاب‌شده معتبر هستند.'))


@admin.register(ProductView)
class ProductViewAdmin(UniversityAccessAdmin):
    list_display = ('product', 'user', 'ip_address', 'timestamp')
    list_filter = ('timestamp', ('product', RelatedDropdownFilter))
    search_fields = ('product__title', 'user__username', 'ip_address')
    readonly_fields = ('timestamp', 'session_key')



