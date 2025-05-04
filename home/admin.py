from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import SiteSetting, FooterLinkBox, FooterLink, Slider,\
    Tag ,SiteOption


@admin.register(SiteOption)
class SiteOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug','logo')

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'site_url', 'email', 'is_main_setting')
    list_filter = ('is_main_setting',)
    search_fields = ('site_name', 'site_url', 'email', 'address')
    ordering = ('-id',)
    filter_horizontal = ('options',)
    fieldsets = (
        (None, {
            'fields': ('site_name', 'site_url','slogan','options', 'address', 'phone', 'fax', 'email', 'site_logo','secondary_logo')
        }),
        ('متن‌ها', {
            'fields': ('copy_right', 'about_us_text')
        }),
        ('تنظیمات اصلی', {
            'fields': ('is_main_setting',),
        }),
    )

class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 1
    fields = ('title', 'url')
    verbose_name = "لینک فوتر"
    verbose_name_plural = "لینک‌های فوتر"

@admin.register(FooterLinkBox)
class FooterLinkBoxAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)
    ordering = ('title',)
    inlines = [FooterLinkInline]

@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'footer_link_box', 'url')
    list_filter = ('footer_link_box',)
    search_fields = ('title', 'url')
    ordering = ('footer_link_box', 'title')

@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ('title', 'url_title', 'is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('order', 'id')
    fieldsets = (
        (None, {
            'fields': ('title', 'url', 'url_title', 'description', 'image')
        }),
        ('تنظیمات', {
            'fields': ('is_active', 'order')
        }),
    )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)