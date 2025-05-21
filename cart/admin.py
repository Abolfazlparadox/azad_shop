from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import Format
from import_export import resources, fields
from weasyprint import HTML
from io import BytesIO
from django.contrib import admin
from .models import Order , OrderItem

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


@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource

    def get_export_formats(self):
        formats = super().get_export_formats()
        formats.append(PDFFormat)  # اینجا بدون پرانتز، خود کلاس را اضافه کنید
        return formats

    def get_export_filename(self, file_format, *args, **kwargs):
        from django.utils.timezone import now
        date_str = now().strftime("%Y-%m-%d")
        if hasattr(file_format, "get_title") and file_format.get_title() == "PDF":
            return f"Order-{date_str}.pdf"
        return super().get_export_filename(file_format, *args, **kwargs)

    list_display = ('id', 'user_display', 'created_at', 'total_price', 'shipping_cost', 'final_price', 'address_display')
    list_filter = ('created_at', 'user', 'address')
    search_fields = ('user__username', 'user__email', 'address__full_address', 'id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 25

    def user_display(self, obj):
        return obj.user.first_name +  obj.user.last_name  if obj.user else "-"
    user_display.short_description = 'کاربر'

    def address_display(self, obj):
        return str(obj.address) if obj.address else "-"
    address_display.short_description = 'آدرس'

class OrderItemResource(resources.ModelResource):
    class Meta:
        model = OrderItem


@admin.register(OrderItem)
class OrderItemAdmin(ImportExportModelAdmin):
    resource_class = OrderItemResource
    list_display = ('id', 'order', 'product', 'variant', 'count', 'unit_price', 'total_price')
    list_filter = ('product', 'variant', 'order__created_at')
    search_fields = ('product__title', 'variant__sku', 'order__user__username', 'order__id')
    ordering = ('-id',)
    list_per_page = 25
