from django.views.generic import ListView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from iranian_cities.models import City
from django.utils.translation import gettext_lazy as _
from account.models import Membership, Address
from django.views.generic.edit import CreateView,DeleteView
from django.urls import reverse_lazy
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, F,Sum, Min, Max
from contact.models import ContactMessage
from product.models import Product, ProductCategory, ProductAttribute, ProductAttributeType, Discount
from unit_admin.forms import CustomUserCreationForm, RoleCreationForm, AddressForm, ProductForm, CategoryForm, \
    AdminSettingsForm, ContactAnswerForm, ProductAttributeForm, ProductAttributeTypeForm, DiscountForm, \
    ProductVariantFormSet, ProductDescriptionFormSet
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class OffiMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')

    def is_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def dispatch(self, request, *args, **kwargs):
        try:
            if request.user.is_authenticated:
                offi = request.user.memberships.get(role='OFFI', is_confirmed=True)
            else:
                raise PermissionDenied(_('شما دسترسی ندارید'))
        except Membership.DoesNotExist :
            print('1')
            raise PermissionDenied(_('شما دسترسی ندارید'))
        self.university = offi.university
        return super().dispatch(request, *args, **kwargs)
class UnitAdminIndexView(OffiMixin, TemplateView):
    template_name = 'unit_admin/index.html'
    login_url = 'login'       # adjust if your login URL name differs
    redirect_field_name = 'next'
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # نمونه: اضافه کردن داده‌های داشبورد
        admin_membership = self.request.user.memberships.get(role='OFFI')
        admin_product =  Product.objects.filter(
            university=admin_membership.university,
        )
        ctx['university'] = admin_membership.university
        ctx['admin_product'] = admin_product
        # ctx['stats'] = ... هر داده‌ی دیگری که می‌خواهید به تمپلیت بدهید
        return ctx

#User
class UserListView(OffiMixin, ListView):
    model = User
    template_name = "unit_admin/users/all-users.html"
    context_object_name = "users"
    paginate_by = 3
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws
    def get_queryset(self):
        try:
            admin_membership = self.request.user.memberships.get(role='OFFI')
            university = admin_membership.university
            return User.objects.filter(
                memberships__university=university,
            ).exclude(id=self.request.user.id).distinct()
        except Membership.DoesNotExist:
            raise PermissionDenied("Access denied.")
class UserCreateView(OffiMixin, CreateView):
    form_class = CustomUserCreationForm
    template_name = "unit_admin/users/add-new-user.html"

    def get_success_url(self):
        return reverse_lazy('unit_admin:user_list')

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws

    def form_valid(self, form):
        user = form.save(commit=False)
        user.email_verified = form.cleaned_data.get('email_verified', False)
        user.is_verified = form.cleaned_data.get('is_verified', False)
        user.save()
        messages.success(self.request, _('کاربر با موفقیت ایجاد شد'))  # پیام فارسی
        Membership.objects.create(
            user=user,
            university=self.request.user.memberships.get(role='OFFI').university,
            role='student',
            is_confirmed=True
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{form.fields[field].label}: {error}")

        messages.error(self.request, "خطاهای زیر را برطرف کنید:")
        messages.error(self.request, "\n".join(error_messages))
        return self.render_to_response(self.get_context_data(form=form))
class UserUpdateView(OffiMixin,UpdateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'unit_admin/users/add-new-user.html'
    context_object_name = 'user_obj'

    def get_form_kwargs(self):
        # pass both current_user and university
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        kwargs['university'] = self.university
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('اطلاعات کاربر با موفقیت به‌روز شد'))
        return redirect('unit_admin:user_list')

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید'))
        return self.render_to_response(self.get_context_data(form=form))
class UserSoftDeleteView(OffiMixin, View):
    """
    حذف نرم کاربر: فقط فیلد is_deleted=True می‌شود، نقش‌ها دست‌نخورده باقی می‌مانند.
    """
    def post(self, request, pk, *args, **kwargs):
        # فقط OFFI تأییدشده می‌تواند کاربر را حذف کند
        user = get_object_or_404(User, pk=pk, is_deleted=False)
        if user == request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'نمی‌توانید خودتان را حذف کنید'
            }, status=400)

        # نرم حذف
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(update_fields=['is_deleted', 'deleted_at'])

        messages.success(request, _('کاربر با موفقیت حذف نرم شد'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('unit_admin:user_list')
class UserHardDeleteView(OffiMixin, View):
    """
    حذف سخت کاربر: اول Membershipهایش حذف می‌شوند، سپس خود رکورد User.
    """
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'نمی‌توانید خودتان را حذف کنید'
            }, status=400)

        # حذف سخت نقش‌ها
        Membership.objects.filter(user=user).delete()
        # حذف سخت کاربر
        user.delete()

        messages.success(request, _('حذف دائمی کاربر با موفقیت انجام شد'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('unit_admin:user_list')

# city
def get_cities(request):
    province_id = request.GET.get('province_id')

    if not province_id:
        return  HttpResponseBadRequest("پارامتر province_id الزامی است")

    try:
        cities = City.objects.filter(province_id=province_id)
    except City.DoesNotExist:
        cities = []

    return render(request, 'unit_admin/includes/city_options.html', {'cities': cities})

#Role
class RoleListView(OffiMixin, ListView):
    model = Membership
    template_name = "unit_admin/roles/all-roll.html"
    context_object_name = "memberships"
    paginate_by = 10
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws
    def get_queryset(self):
        try:
            university = self.request.user.memberships.get(role='OFFI').university
            return Membership.objects.filter(
                university=university
            ).exclude(user=self.request.user).distinct()
        except Membership.DoesNotExist:
            raise PermissionDenied("Access denied.")
class RoleCreateView(OffiMixin, CreateView):
    form_class    = RoleCreationForm
    template_name = "unit_admin/roles/add-new-roll.html"
    success_url   = reverse_lazy('unit_admin:role_list')

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['current_user'] = self.request.user
        kws['university'] = self.university
        return kws

    def form_valid(self, form):
        membership = form.save(commit=False)
        membership.university   = form.university
        membership.is_confirmed = True
        membership.confirmed_at = timezone.now()
        membership.save()
        messages.success(self.request, "نقش با موفقیت اضافه شد")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "لطفا خطاهای فرم را بررسی کنید")
        return super().form_invalid(form)
class RoleUpdateView(OffiMixin,UpdateView):
    model = Membership
    form_class = RoleCreationForm
    template_name = 'unit_admin/roles/add-new-roll.html'
    context_object_name = 'membership_obj'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        kwargs['university']   = self.request.user.memberships.get(role='OFFI').university
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('نقش با موفقیت به‌روز شد'))
        return redirect('unit_admin:role_list')

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در به‌روز‌رسانی نقش'))
        return super().form_invalid(form)
class RoleDeleteView(OffiMixin, View):
    def post(self, request, pk, *args, **kwargs):
        membership = get_object_or_404(
            Membership,
            pk=pk,
            university=self.university
        )
        # (optional) Prevent deleting own OFFI role…
        membership.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        messages.success(request, "نقش با موفقیت حذف شد")
        return redirect('unit_admin:role_list')

#Address
class AddressListView(OffiMixin, ListView):
    model = Address
    template_name = 'unit_admin/addresses/address_list.html'
    context_object_name = 'addresses'
    paginate_by = 10
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['current_user'] = self.request.user
        kws['university'] = self.university
        return kws
class AddressCreateView(OffiMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'unit_admin/addresses/address_form.html'
    success_url = reverse_lazy('unit_admin:address_list')
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university  # از OffiMixin گرفته شده
        return kws
    def form_valid(self, form):
        messages.success(self.request, _('نشانی با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)
class AddressUpdateView(OffiMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'unit_admin/addresses/address_form.html'
    success_url = reverse_lazy('unit_admin:address_list')

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws
    def get_object(self, queryset=None):
        return get_object_or_404(
            Address.objects.filter(
                user__memberships__university=self.university,
                user__memberships__is_confirmed=True,
            ), pk=self.kwargs['pk'])

    def form_valid(self, form):
        messages.success(self.request, _('نشانی با موفقیت بروزرسانی شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در بروزرسانی نشانی'))
        return super().form_invalid(form)
class AddressDeleteView(OffiMixin, View):
    def post(self, request, pk, *args, **kwargs):
        address = get_object_or_404(
            Address.objects.filter(user__memberships__university=self.university),pk=pk)
        address.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        messages.success(request, "نشانی با موفقیت حذف شد")
        return redirect('unit_admin:address_list')

class ProductAttributeTypeListView(OffiMixin, ListView):
    model = ProductAttributeType
    template_name = 'unit_admin/product_attributes/type_list.html'
    context_object_name = 'types'
    paginate_by = 10

    def get_queryset(self):
        # اگر نیاز به فیلتر دانشگاه دارید:
        return ProductAttributeType.objects.all().order_by('name')
class AttributeTypeCreateView(OffiMixin, CreateView):
    model = ProductAttributeType
    form_class = ProductAttributeTypeForm
    template_name = 'unit_admin/product_attributes/type_form.html'
    success_url = reverse_lazy('unit_admin:attribute_type_list')
class AttributeTypeUpdateView(AttributeTypeCreateView, UpdateView):
    success_url = reverse_lazy('unit_admin:attribute_type_list')
class AttributeTypeDeleteView(OffiMixin, DeleteView):
    model = ProductAttributeType
    success_url = reverse_lazy('unit_admin:attribute_type_list')

# مشابه برای ProductAttribute
class ProductAttributeListView(OffiMixin, ListView):
    model = ProductAttribute
    template_name = 'unit_admin/product_attributes/value_list.html'
    context_object_name = 'attributes'
    paginate_by = 10

    def get_queryset(self):
        # فیلتر به‌اختیار؛ اینجا همه را نمایش می‌دهیم
        return ProductAttribute.objects.select_related('type').order_by('type__name', 'value')
class AttributeCreateView(OffiMixin, CreateView):
    model = ProductAttribute
    form_class = ProductAttributeForm
    template_name = 'unit_admin/product_attributes/value_form.html'
    success_url = reverse_lazy('unit_admin:attribute_list')
class AttributeUpdateView(AttributeCreateView, UpdateView):
    success_url = reverse_lazy('unit_admin:attribute_list')
class AttributeDeleteView(OffiMixin, DeleteView):
    model = ProductAttribute
    success_url = reverse_lazy('unit_admin:attribute_list')

# و برای Discount
class DiscountListView(OffiMixin, ListView):
    model = Discount
    template_name = 'unit_admin/discounts/discount_list.html'
    context_object_name = 'discounts'
    paginate_by = 10

    def get_queryset(self):
        # فیلتر تخفیف‌های مرتبط با دانشگاه مدیر
        return Discount.objects.filter(
            Q(products__university=self.university) |
            Q(categories__university=self.university)
        ).distinct().order_by('-valid_to')
class DiscountCreateView(OffiMixin, CreateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'unit_admin/discounts/discount_form.html'
    success_url = reverse_lazy('unit_admin:discount_list')

    def form_valid(self, form):
        # used_count را صفر نگه می‌داریم؛ ارتباط با سفارش بعداً
        return super().form_valid(form)
class DiscountUpdateView(DiscountCreateView, UpdateView):
    success_url = reverse_lazy('unit_admin:discount_list')
class DiscountDeleteView(OffiMixin, DeleteView):
    model = Discount
    success_url = reverse_lazy('unit_admin:discount_list')
# Product
class ProductListView(OffiMixin, ListView):
    model = Product
    template_name = 'unit_admin/products/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        qs = Product.objects.filter(university=self.university).annotate(
            total_stock=Sum('variants__stock'),
            min_price=Min(
                'variants__price_override',
                filter=Q(variants__price_override__isnull=False)
            ),
            max_price=Max(
                'variants__price_override',
                filter=Q(variants__price_override__isnull=False)
            )
        ).order_by('-created_at').distinct()
        return qs
class ProductCreateView(OffiMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'unit_admin/products/product_form.html'
    success_url = reverse_lazy('unit_admin:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # اگر یک instance قبلاً ساخته شده باشد (بعد از save فرم اصلی)
        obj = getattr(self, 'object', None)
        if self.request.method == 'POST':
            ctx['variant_formset']     = ProductVariantFormSet(self.request.POST, instance=obj)
            ctx['description_formset'] = ProductDescriptionFormSet(self.request.POST, self.request.FILES, instance=obj)
        else:
            ctx['variant_formset']     = ProductVariantFormSet(instance=obj)
            ctx['description_formset'] = ProductDescriptionFormSet(instance=obj)
        return ctx

    def form_valid(self, form):
        # ذخیرهٔ اولیهٔ محصول
        form.instance.university = self.university
        self.object = form.save()

        # بارگذاری فرم‌ست‌ها از request
        variant_fs     = ProductVariantFormSet(self.request.POST, instance=self.object)
        description_fs = ProductDescriptionFormSet(self.request.POST, self.request.FILES, instance=self.object)

        # اعتبارسنجی هر دو فرم‌ست
        if variant_fs.is_valid() and description_fs.is_valid():
            variant_fs.save()
            description_fs.save()
            messages.success(self.request, _('محصول با موفقیت ایجاد شد'))
            return redirect(self.success_url)
        else:
            # اگر فرم‌ست‌ها خطا دارند، خطاها را به قالب بفرست
            messages.error(self.request, _('خطا در تنوع‌ها یا توضیحات محصول'))
            return self.render_to_response(self.get_context_data(form=form))



    def form_invalid(self, form):
        ctx = self.get_context_data(form=form)
        variant_fs = ctx['variant_formset']
        description_fs = ctx['description_formset']

        logger.error("MAIN FORM ERRORS: %s", form.errors)
        logger.error("VARIANT FS ERRORS: %s", variant_fs.errors)
        logger.error("DESCRIPTION FS ERRORS: %s", description_fs.errors)

        messages.error(self.request, _('لطفاً خطاهای فرم اصلی و فرم‌ست‌ها را بررسی کنید'))
        return self.render_to_response(ctx)
class ProductUpdateView(OffiMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'unit_admin/products/product_form.html'
    success_url = reverse_lazy('unit_admin:product_list')

    def get_object(self):
        return get_object_or_404(Product, pk=self.kwargs['pk'], university=self.university)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            variant_fs = ProductVariantFormSet(self.request.POST, instance=self.object)
            desc_fs = ProductDescriptionFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            variant_fs = ProductVariantFormSet(instance=self.object)
            desc_fs = ProductDescriptionFormSet(instance=self.object)
        ctx['variant_formset'] = variant_fs
        ctx['variant_empty_form'] = variant_fs.empty_form
        ctx['description_formset'] = desc_fs
        ctx['description_empty_form'] = desc_fs.empty_form
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        variant_fs     = ctx['variant_formset']
        description_fs = ctx['description_formset']
        if variant_fs.is_valid() and description_fs.is_valid():
            self.object = form.save()
            variant_fs.instance = self.object
            variant_fs.save()
            description_fs.instance = self.object
            description_fs.save()
            messages.success(self.request, _('محصول با موفقیت به‌روز شد'))
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))
class ProductSoftDeleteView( OffiMixin, View):
    """Soft-delete: set is_deleted=True"""
    def post(self, request, pk):
        prod = get_object_or_404(
            Product,
            pk=pk,
            university=self.university,
            is_deleted=False
        )
        prod.is_deleted = True
        prod.save(update_fields=['is_deleted'])
        messages.success(request, _('محصول با موفقیت حذف (نرم) شد'))
        return redirect('unit_admin:product_list')
class ProductHardDeleteView( OffiMixin, DeleteView):
    """Permanent delete"""
    model = Product
    success_url = reverse_lazy('unit_admin:product_list')

    def get_object(self, queryset=None):
        return get_object_or_404(
            Product,
            pk=self.kwargs['pk'],
            university=self.university
        )

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('محصول به صورت دائمی حذف شد'))
        return super().delete(request, *args, **kwargs)


# Category
class CategoryListView(OffiMixin, ListView):
    template_name = "unit_admin/categories/categories-list.html"
    paginate_by = 5
    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['current_user'] = self.request.user
        kws['university'] = self.university
        return kws
    def get_queryset(self):
        # return the flat rows list instead of model instances
        qs = ProductCategory.objects.filter(
            university=self.university, is_deleted=False
        ).order_by('parent__id','title')
        parents = [c for c in qs if c.parent is None]
        child_map = {}
        for c in qs:
            if c.parent_id:
                child_map.setdefault(c.parent_id, []).append(c)
        rows = []
        for p in parents:
            rows.append((p,0))
            for ch in child_map.get(p.pk, []):
                rows.append((ch,1))
        return rows  # now ListView will paginate this list

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # 'object_list' is already the paginated slice of rows
        ctx['rows'] = ctx['object_list']
        return ctx
class CategoryCreateView(OffiMixin, CreateView):
    model = ProductCategory
    form_class = CategoryForm
    template_name = "unit_admin/categories/category-form.html"
    success_url = reverse_lazy('unit_admin:category_list')

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws

    def form_valid(self, form):
        messages.success(self.request, _('دسته‌بندی جدید با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را برطرف کنید'))
        return super().form_invalid(form)

class CategoryUpdateView(OffiMixin, UpdateView):
    model = ProductCategory
    form_class = CategoryForm
    template_name = "unit_admin/categories/category-form.html"
    success_url = reverse_lazy('unit_admin:category_list')

    def get_object(self):
        return get_object_or_404(
            ProductCategory,
            pk=self.kwargs['pk'],
            university=self.university
        )

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws

    def form_valid(self, form):
        messages.success(self.request, _('دسته‌بندی با موفقیت به‌روز شد'))
        return super().form_valid(form)
class CategorySoftDeleteView(OffiMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(
            ProductCategory,
            pk=pk, university=self.university, is_deleted=False
        )
        obj.is_deleted = True
        obj.save(update_fields=['is_deleted'])
        messages.success(request, _('حذف نرم انجام شد'))
        return redirect('unit_admin:category_list')
class CategoryHardDeleteView(OffiMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(
            ProductCategory,
            pk=pk, university=self.university
        )
        obj.delete()
        messages.success(request, _('حذف دائم انجام شد'))
        return redirect('unit_admin:category_list')

class AdminSettingsView(OffiMixin, TemplateView):
    template_name = 'unit_admin/settings/settings.html'


    def get(self, request, *args, **kwargs):
        user = request.user
        form = AdminSettingsForm(instance=user)
        addresses = Address.objects.filter(user=user)

        # ۱) نام‌های فیلد فقط‌خواندنی:
        readonly_names = [
            'is_verified','is_staff','is_active',
            'marketing_consent','terms_accepted',
            'email_verified','is_deleted'
        ]
        # ۲) ساخت لیست BoundField:
        readonly_fields = [form[name] for name in readonly_names if name in form.fields]

        return render(request, self.template_name, {
            'form': form,
            'addresses': addresses,
            'readonly_fields': readonly_fields,
        })

    def post(self, request, *args, **kwargs):
        user = request.user
        form = AdminSettingsForm(request.POST, request.FILES, instance=user)
        addresses = Address.objects.filter(user=user)

        readonly_names = [ ... ]  # همان لیست بالا
        readonly_fields = [form[name] for name in readonly_names if name in form.fields]

        if form.is_valid():
            form.save()
            messages.success(request, _('اطلاعات با موفقیت به‌روز شد'))
            return redirect('unit_admin:settings')

        messages.error(request, _('لطفاً خطاهای فرم را بررسی کنید'))
        return render(request, self.template_name, {
            'form': form,
            'addresses': addresses,
            'readonly_fields': readonly_fields,
        })
class AdminAddressDeleteView(OffiMixin, View):
    """
    حذف سخت یک آدرس از لیست تنظیمات
    """
    def post(self, request, pk, *args, **kwargs):
        addr = get_object_or_404(Address, pk=pk, user=request.user)
        addr.delete()
        messages.success(request, _('نشانی حذف شد'))
        return redirect('unit_admin:settings')


class ContactMessageListView(OffiMixin, ListView):
    model = ContactMessage
    template_name = "unit_admin/contact/message_list.html"
    context_object_name = "messages"
    paginate_by = 5

    def get_queryset(self):
        qs = super().get_queryset()
        # فقط تیکت‌های دانشگاه خود OFFI
        qs = qs.filter(university=self.university)
        # جستجو در نام، نام خانوادگی یا ایمیل
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
        return qs.order_by("-created_at")

    def render_to_response(self, context, **response_kwargs):
        # اگر AJAX باشد، فقط جدول را برگردان
        if self.is_ajax():
            return render(self.request, "unit_admin/contact/_message_table.html", context)
        return super().render_to_response(context, **response_kwargs)
class ContactMessageAnswerView(OffiMixin, UpdateView):
    model = ContactMessage
    form_class = ContactAnswerForm
    template_name = "unit_admin/contact/message_answer.html"
    context_object_name = "message"
    pk_url_kwarg = "pk"
    success_url = reverse_lazy("unit_admin:contact_list")

    def get_object(self, queryset=None):
        obj = get_object_or_404(ContactMessage, pk=self.kwargs["pk"], university=self.university)
        return obj

    def form_valid(self, form):
        msg = form.save(commit=False)
        msg.status = "answered"
        msg.responded_at = timezone.now()
        msg.save()
        messages.success(self.request, "پیام با موفقیت پاسخ داده شد.")
        return super().form_valid(form)

class OrdersListView( OffiMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/orders/list.html"
    context_object_name = 'orders'
    ordering = ['-created_at']
    paginate_by = 15
class TaxListView( OffiMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/tax/list.html"
    context_object_name = 'taxes'
    ordering = ['-rate']
class ReportsListView( OffiMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/reports/list.html"
    context_object_name = 'reports'
    ordering = ['-generated_at']