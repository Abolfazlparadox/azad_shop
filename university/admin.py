# university/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import University

class UniversityAdminForm(forms.ModelForm):
    name_suffix = forms.CharField(
        label=_('نام اختصاصی'),
        help_text=_('فقط قسمت بعد از "دانشگاه آزاد" را وارد کنید (مثال: مرکزی)')
    )

    class Meta:
        model = University
        fields = '__all__'
        labels = {
            'status': _('وضعیت فعال/غیرفعال'),
            'post_code': _('کد پستی'),
        }
        help_texts = {
            'website': _('آدرس کامل با http:// یا https://'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.name.startswith("دانشگاه آزاد "):
            self.initial['name_suffix'] = self.instance.name[13:]

    def clean_name_suffix(self):
        suffix = self.cleaned_data['name_suffix']
        if not suffix:
            raise ValidationError(_("این فیلد نمی‌تواند خالی باشد"))
        return suffix.strip()

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    form = UniversityAdminForm
    list_display = (
        'name_display',
        'status_badge',
        'established_year',
        'contact_info',
        'logo_thumbnail',
        'province',
        'city',
    )
    list_filter = (
        'status',
        ('established_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'name__icontains',
        'address__icontains',
        'post_code__icontains',
    )
    readonly_fields = (
        'slug',
        'logo_preview',
    )
    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': (
                'status',
                'name_suffix',
                'slug',
                'established_date',
                # 'description',
            )
        }),
        (_('موقعیت جغرافیایی'), {
            'fields': (
                'province',
                'city',
                'address',
                'post_code',
            )
        }),
        (_('اطلاعات تماس'), {
            'fields': (
                'phone_number',
                'email',
                'website',
            )
        }),
        (_('رسانه'), {
            'fields': (
                'logo',
                'logo_preview',
            )
        }),
    )
    actions = ['activate_selected', 'deactivate_selected']

    # نمایش سفارشی
    def name_display(self, obj):
        return obj.name
    name_display.short_description = _('نام دانشگاه')
    name_display.admin_order_field = 'name'

    def status_badge(self, obj):
        color = 'success' if obj.status else 'secondary'
        text = _('فعال') if obj.status else _('غیرفعال')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            text
        )
    status_badge.short_description = _('وضعیت')

    def established_year(self, obj):
        return obj.established_date.year
    established_year.short_description = _('سال تأسیس')
    established_year.admin_order_field = 'established_date'

    def contact_info(self, obj):
        return format_html(
            "{}<br>{}",
            obj.phone_number,
            obj.email
        )
    contact_info.short_description = _('تماس')

    def logo_thumbnail(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 50px; width: auto;">',
                obj.logo.url
            )
        return _("بدون تصویر")
    logo_thumbnail.short_description = _('لوگو')

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-width: 300px; height: auto;">',
                obj.logo.url
            )
        return _("تصویری انتخاب نشده است")
    logo_preview.short_description = _('پیش نمایش لوگو')

    # اکشن‌های مدیریتی
    def activate_selected(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, _('{} دانشگاه فعال شدند').format(updated))
    activate_selected.short_description = _('فعال کردن دانشگاه‌های انتخاب شده')

    def deactivate_selected(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, _('{} دانشگاه غیرفعال شدند').format(updated))
    deactivate_selected.short_description = _('غیرفعال کردن دانشگاه‌های انتخاب شده')

    # بهینه‌سازی عملکرد
    def get_queryset(self, request):
        return super().get_queryset(request).select_related().prefetch_related()

    # ذخیره سازی سفارشی
    def save_model(self, request, obj, form, change):
        obj.name = f"دانشگاه آزاد {form.cleaned_data['name_suffix']}"
        super().save_model(request, obj, form, change)