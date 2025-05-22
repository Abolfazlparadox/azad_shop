from django.contrib import admin
from .models import Order, OrderItem, Cart, CartDetail
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import Format
from import_export import resources, fields
from weasyprint import HTML
from io import BytesIO
from jalali_date.admin import ModelAdminJalaliMixin


# ===== PDF FORMAT CLASS =====
class PDFFormat(Format):
    def get_title(self):
        return "PDF"

    def get_extensions(self):
        return ["pdf"]

    def get_content_type(self):
        return "application/pdf"

    def generate_html(self, dataset):
        html = "<html lang='fa' dir='rtl'><head><meta charset='UTF-8'/><style>body {font-family: Tahoma, Arial, sans-serif; font-size: 12px;} table {border-collapse: collapse; width: 100%;} th, td {border: 1px solid #333; padding: 8px; text-align: center;} th {background-color: #f2f2f2;} h2 {text-align: center;}</style></head><body><h2>گزارش خروجی</h2><table><thead><tr>"
        html += "".join(f"<th>{col}</th>" for col in dataset.headers)
        html += "</tr></thead><tbody>"
        for row in dataset.dict:
            html += "<tr>" + "".join(f"<td>{row[col]}</td>" for col in dataset.headers) + "</tr>"
        html += "</tbody></table></body></html>"
        return html

    def export_data(self, dataset, **kwargs):
        pdf_buffer = BytesIO()
        HTML(string=self.generate_html(dataset)).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()

    def can_export(self):
        return True

    def can_import(self):
        return False


# ===== RESOURCES =====
class CartResource(resources.ModelResource):
    class Meta:
        model = Cart

class CartDetailResource(resources.ModelResource):
    class Meta:
        model = CartDetail

class OrderResource(resources.ModelResource):
    user_display = fields.Field(column_name='کاربر')
    address_display = fields.Field(column_name='آدرس')

    def dehydrate_user_display(self, order):
        return order.user.first_name + order.user.last_name if order.user else "-"

    def dehydrate_address_display(self, order):
        return str(order.address) if order.address else "-"

    class Meta:
        model = Order
        fields = ('id', 'user_display', 'created_at', 'total_price', 'shipping_cost', 'final_price', 'address_display')
        export_order = ('id', 'user_display', 'created_at', 'total_price', 'shipping_cost', 'final_price', 'address_display')

class OrderItemResource(resources.ModelResource):
    id = fields.Field(attribute='id', column_name='شناسه')
    product_name = fields.Field(column_name='نام محصول')
    user_name = fields.Field(column_name='نام کاربر')
    variant_attributes = fields.Field(column_name='ویژگی‌های تنوع')
    count = fields.Field(attribute='count', column_name='تعداد')
    unit_price = fields.Field(attribute='unit_price', column_name='قیمت واحد هر محصول')
    total_price = fields.Field(attribute='total_price', column_name='جمع کل با احتساب تخفیف')

    def dehydrate_id(self, obj):
        return obj.id

    def dehydrate_product_name(self, obj):
        return obj.product.title + " - " + obj.product.university.name if obj.product else "-"

    def dehydrate_user_name(self, obj):
        if obj.order and obj.order.user:
            return f"{obj.order.user.first_name} {obj.order.user.last_name}"
        return "-"

    def dehydrate_variant_attributes(self, obj):
        if not obj.variant:
            return "-"
        attrs = []
        for attr in obj.variant.attributes.all():
            if attr.type and attr.value:
                attrs.append(f"{attr.type.name} : {attr.value}")
        return ", ".join(attrs)

    def dehydrate_count(self, obj):
        return obj.count

    def dehydrate_unit_price(self, obj):
        return obj.unit_price

    def dehydrate_total_price(self, obj):
        return obj.total_price

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product_name',
            'user_name',
            'variant_attributes',
            'count',
            'unit_price',
            'total_price'
        )
        export_order = (
            'id',
            'product_name',
            'user_name',
            'variant_attributes',
            'count',
            'unit_price',
            'total_price'
        )

# ===== INLINE =====
class CartDetailInline(admin.TabularInline):
    model = CartDetail
    extra = 0
    readonly_fields = ['final_price', 'get_total_price', 'discount_amount', 'total_discount']
    fields = ['product', 'variant', 'count', 'final_price', 'get_total_price', 'discount_amount', 'total_discount']
    show_change_link = True

    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = "قیمت کل"

    def discount_amount(self, obj):
        return obj.discount_amount
    discount_amount.short_description = "تخفیف تکی"

    def total_discount(self, obj):
        return obj.total_discount
    total_discount.short_description = "مجموع تخفیف"


# ===== ADMINS =====
@admin.register(Cart)
class CartAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    resource_class = CartResource
    inlines = [CartDetailInline]
    list_display = ['id', 'user', 'is_paid', 'payment_date', 'calculate_total_price', 'created_at', 'updated_at']
    list_filter = ['is_paid', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['calculate_total_price', 'created_at', 'updated_at']

    def calculate_total_price(self, obj):
        return obj.calculate_total_price()
    calculate_total_price.short_description = "قیمت کل سبد"

    def get_export_formats(self):
        formats = super().get_export_formats()
        formats.append(PDFFormat)
        return formats


@admin.register(CartDetail)
class CartDetailAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    resource_class = CartDetailResource
    list_display = ['id', 'cart', 'product', 'variant', 'count', 'final_price', 'get_total_price', 'total_discount']
    list_filter = ['product', 'created_at']
    search_fields = ['product__title', 'variant__sku', 'cart__user__username']
    readonly_fields = ['get_total_price', 'discount_amount', 'total_discount', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = "قیمت کل"

    def discount_amount(self, obj):
        return obj.discount_amount
    discount_amount.short_description = "تخفیف تکی"

    def total_discount(self, obj):
        return obj.total_discount
    total_discount.short_description = "مجموع تخفیف"

    def get_export_formats(self):
        formats = super().get_export_formats()
        formats.append(PDFFormat)
        return formats


@admin.register(Order)
class OrderAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = ('id', 'user_display', 'created_at', 'total_price', 'shipping_cost', 'final_price', 'address_display')
    list_filter = ('created_at', 'user', 'address')
    search_fields = ('user__username', 'user__email', 'address__full_address', 'id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def user_display(self, obj):
        return obj.user.first_name + obj.user.last_name if obj.user else "-"
    user_display.short_description = 'کاربر'

    def address_display(self, obj):
        return str(obj.address) if obj.address else "-"
    address_display.short_description = 'آدرس'

    def get_export_formats(self):
        formats = super().get_export_formats()
        formats.append(PDFFormat)
        return formats


@admin.register(OrderItem)
class OrderItemAdmin(ModelAdminJalaliMixin, ImportExportModelAdmin):
    resource_class = OrderItemResource
    list_display = (
        'id',
        'order_display',
        'product_name',
        'variant_attributes_display',
        'count',
        'unit_price',
        'total_price'
    )
    list_filter = ('product', 'variant', 'order__created_at')
    search_fields = ('product__title', 'variant__sku', 'order__user__username', 'order__id')
    ordering = ('-id',)

    def order_display(self, obj):
        user_name = f"{obj.order.user.first_name} {obj.order.user.last_name}" if obj.order.user else "-"
        return f"سفارش شماره {obj.order.id} به نام {user_name}"
    order_display.short_description = "سفارش"

    def product_name(self, obj):
        return obj.product.title  + " - " + obj.product.university.name if obj.product else "-"
    product_name.short_description = "نام محصول"

    def variant_attributes_display(self, obj):
        if not obj.variant:
            return "-"
        attrs = []
        for attr in obj.variant.attributes.all():
            if attr.type and attr.value:
                attrs.append(f"{attr.type.name} : {attr.value}")
        return ", ".join(attrs)
    variant_attributes_display.short_description = "ویژگی‌های تنوع"
    def count(self, obj):
        return obj.count
    count.short_description = "تعداد"

    def unit_price(self, obj):
        return obj.unit_price
    unit_price.short_description = "قیمت واحد هر محصول"

    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = "جمع کل با احتساب تخفیف"

    def id_display(self, obj):
        return obj.id

    id_display.short_description = "شناسه"

    def get_export_formats(self):
        formats = super().get_export_formats()
        formats.append(PDFFormat)
        return formats
