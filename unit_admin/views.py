from django.db import IntegrityError
from django.template.loader import render_to_string
from django.views.generic import ListView, TemplateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from iranian_cities.models import City
from django.utils.translation import gettext_lazy as _
from account.models import Membership, Address
from django.views.generic.edit import CreateView,DeleteView
from django.urls import reverse_lazy
from django.views import View
from weasyprint import HTML, CSS
from blog.models import BlogPost
from cart.models import Order, OrderItem
from comment.models import Comment
from utility.category_tree import build_category_tree
from django.core.paginator import Paginator
from django.db.models import Q, F, Sum, Min, Max, Count, DecimalField, IntegerField
from contact.models import ContactMessage
from product.models import Product, ProductCategory, ProductAttribute, ProductAttributeType, Discount
from unit_admin.forms import CustomUserCreationForm, RoleCreationForm, AddressForm, ProductForm, CategoryForm, \
    AdminSettingsForm, ContactAnswerForm, ProductAttributeForm, ProductAttributeTypeForm, DiscountForm, \
    ProductVariantFormSet, ProductDescriptionFormSet, BlogPostForm
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest, Http404, HttpResponse
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
    login_url = 'login'

    def get_context_data(self, **kwargs):
        from django.db.models import Sum, Count, F, DecimalField, IntegerField, Max
        from django.db.models.functions import TruncMonth
        import datetime
        import jdatetime  # برای تبدیل به سال خورشیدی

        ctx = super().get_context_data(**kwargs)
        uni = self.university

        # آمار کلی
        ctx['users_number'] = User.objects.filter(memberships__university=uni).count() - 1
        ctx['category']     = ProductCategory.objects.filter(parent=None)

        # پرفروش‌ترین ۳ محصول
        best = (
            Product.objects
                   .filter(university=uni)
                   .annotate(
                       total_sold=Sum('orderitem__total_price', output_field=DecimalField()),
                       total_qty =Sum('orderitem__count',       output_field=IntegerField()),
                       last_sold =Max('orderitem__order__created_at'),
                       available_stock=Sum('variants__stock',    output_field=IntegerField()),
                   )
                   .order_by('-total_sold')[:3]
        )
        ctx['best_selling'] = best

        # سفارشات اخیر
        recent = (
            Order.objects
                 .filter(items__product__university=uni)
                 .annotate(
                     university_items_count = Count('items', distinct=True),
                     university_total_price = Sum('items__total_price', output_field=DecimalField()),
                 )
                 .distinct()
                 .order_by('-created_at')[:4]
        )
        ctx['recent_orders'] = recent
        # گزارش کل درآمد از ابتدا تا امروز
        total_earnings = (
                OrderItem.objects
                .filter(product__university=uni, order__status=Order.STATUS_CONFIRMED)
                .aggregate(sum=Sum('total_price'))['sum'] or 0
        )

        # تعداد کل سفارشات از ابتدا تا امروز
        total_orders = (
            Order.objects
            .filter(items__product__university=uni)
            .distinct()
            .count()
        )

        ctx['total_earnings'] = total_earnings
        ctx['total_orders'] = total_orders
        ctx['admin_product_count'] = Product.objects.filter(university=uni).count()
        # گزارش درآمد ماهانه (12 ماه گذشته)
        qs = (
            OrderItem.objects
                     .filter(
                         product__university=uni,
                         order__status=Order.STATUS_CONFIRMED
                     )
                     .annotate(month=TruncMonth('order__created_at'))
                     .values('month')
                     .annotate(data=Sum('total_price'))
                     .order_by('month')
        )
        # Prepare last 12 months labels and values, in Jalali calendar
        today = datetime.date.today().replace(day=1)
        labels = []
        data = []
        for i in range(11, -1, -1):
            # calculate Gregorian month
            month_offset = (today.month - i - 1) % 12 + 1
            year_offset = today.year - ((today.month - i - 1) // 12 + 1) if today.month - i <= 0 else today.year
            g_date = datetime.date(year_offset, month_offset, 1)
            # convert to Jalali
            j_date = jdatetime.date.fromgregorian(date=g_date)
            # format as 'YYYY-MM'
            labels.append(f"{j_date.year}-{j_date.month:02d}")
            # find sum in qs
            total = next((item['data'] for item in qs if item['month'].date() == g_date), 0)
            data.append(float(total or 0))
        ctx['earnings_chart'] = {'labels': labels, 'data': data}
        return ctx


#User
class UserListView(OffiMixin, ListView):
    model = User
    template_name = "unit_admin/users/all-users.html"
    context_object_name = "users"
    paginate_by = 10  # می‌توانید به 3 تغییر دهید

    def get_queryset(self):
        # فقط کاربران دانشگاه فعال (OFFI)
        qs = super().get_queryset().filter(
            memberships__university=self.university
        ).exclude(id=self.request.user.id).distinct()

        # فیلتر جستجوی AJAX / فرم
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
        return qs.order_by('first_name', 'last_name')

    def render_to_response(self, context, **response_kwargs):
        # اگر AJAX باشد، فقط partial جدول را برگردان
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                "unit_admin/users/_user_table.html",
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
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

    def get_queryset(self):
        university = self.university
        qs = Membership.objects.filter(university=university).exclude(user=self.request.user)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q)
            )
        return qs.order_by('-confirmed_at')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                "unit_admin/roles/_role_table.html",
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
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

    def get_queryset(self):
        # فقط نشانی‌های کاربرانی که در دانشگاه جاری عضو هستند
        qs = Address.objects.filter(
            user__memberships__university=self.university
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(postal_code__icontains=q)
            )
        return qs.order_by('-created_at').distinct()

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                'unit_admin/addresses/_address_table.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
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
    paginate_by = 2

    def get_queryset(self):
        # پایه: مرتب شده بر نام
        qs = ProductAttributeType.objects.all().order_by('name')

        # اگر پارامتر جستجو ارسال شده باشد، فیلتر کن
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q))
        return qs

    def render_to_response(self, context, **response_kwargs):
        # اگر درخواست AJAX باشد، فقط partial جدول را برگردان
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                'unit_admin/product_attributes/_type_table.html',
                context,
                **response_kwargs
            )
        # در غیر این صورت هدر و بادی کامل
        return super().render_to_response(context, **response_kwargs)
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect(self.success_url)

# مشابه برای ProductAttribute
class ProductAttributeListView(OffiMixin, ListView):
    model = ProductAttribute
    template_name = 'unit_admin/product_attributes/value_list.html'
    context_object_name = 'attributes'
    paginate_by = 10

    def get_queryset(self):
        qs = ProductAttribute.objects.select_related('type').order_by('type__name', 'value')
        # فقط موارد دانشگاه جاری:
        # جستجو در فیلد مقدار
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(value__icontains=q)
        return qs

    def render_to_response(self, context, **response_kwargs):
        # اگر AJAX باشد، فقط partial جدول را برگردان
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                'unit_admin/product_attributes/_value_table.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
class AttributeCreateView(OffiMixin, CreateView):
    model = ProductAttribute
    form_class = ProductAttributeForm
    template_name = 'unit_admin/product_attributes/value_form.html'
    success_url = reverse_lazy('unit_admin:value_list')
class AttributeUpdateView(AttributeCreateView, UpdateView):
    success_url = reverse_lazy('unit_admin:value_list')
class AttributeDeleteView(OffiMixin, DeleteView):
    model = ProductAttribute
    success_url = reverse_lazy('unit_admin:value_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # مطمئن می‌شویم این مقدار ویژگی متعلق به دانشگاه ما باشد
        if obj.type and hasattr(obj.type, 'university') and obj.type.university != self.university:
            raise Http404
        return obj

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect(self.success_url)

# و برای Discount
class DiscountListView(OffiMixin, ListView):
    model = Discount
    template_name = 'unit_admin/discounts/discount_list.html'
    context_object_name = 'discounts'
    paginate_by = 10

    def get_queryset(self):
        qs = Discount.objects.distinct().order_by('-valid_to')
        q = self.request.GET.get('q','').strip()
        if q:
            qs = qs.filter(code__icontains=q)
        return qs

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                'unit_admin/discounts/_discount_table.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
class DiscountCreateView(OffiMixin, CreateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'unit_admin/discounts/discount_form.html'
    success_url = reverse_lazy('unit_admin:discount_list')

    def form_valid(self, form):
        messages.success(self.request, _('تخفیف با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)
class DiscountUpdateView(OffiMixin, UpdateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'unit_admin/discounts/discount_form.html'
    success_url = reverse_lazy('unit_admin:discount_list')

    def form_valid(self, form):
        messages.success(self.request, _('تخفیف با موفقیت به‌روز شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)
class DiscountDeleteView(OffiMixin, DeleteView):
    model = Discount
    success_url = reverse_lazy('unit_admin:discount_list')

    def delete(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            self.object = self.get_object()
            self.object.delete()
            return JsonResponse({'status':'success'})
        messages.success(request, _('تخفیف با موفقیت حذف شد'))
        return super().delete(request, *args, **kwargs)

# Product
class ProductListView(OffiMixin, ListView):
    model = Product
    template_name = 'unit_admin/products/product_list.html'
    context_object_name = 'products'
    paginate_by = 2

    def get_queryset(self):
        qs = Product.objects.filter(university=self.university).annotate(
            total_stock=Sum('variants__stock'),
            min_price=Min('variants__price', filter=Q(variants__price__isnull=False)),
            max_price=Max('variants__price', filter=Q(variants__price__isnull=False))
        ).distinct().order_by('-created_at')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        return qs

    def render_to_response(self, context, **response_kwargs):
        # اگر AJAX باشد فقط tbody را برگردان
        if self.request.GET.get('ajax') == '1':
            return render(
                self.request,
                'unit_admin/products/_product_rows.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
class ProductCreateView(OffiMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'unit_admin/products/product_form.html'
    success_url = reverse_lazy('unit_admin:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['variant_formset']     = ProductVariantFormSet(self.request.POST or None, instance=self.object,    prefix='variants',)
        ctx['description_formset'] = ProductDescriptionFormSet(self.request.POST or None, self.request.FILES or None, instance=self.object,    prefix='descriptions',)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        vf = ctx['variant_formset']
        df = ctx['description_formset']
        if vf.is_valid() and df.is_valid():
            form.instance.university = self.university
            self.object = form.save()
            vf.instance = self.object; vf.save()
            df.instance = self.object; df.save()
            messages.success(self.request, _('محصول با موفقیت ذخیره شد'))
            return redirect(self.success_url)
        messages.error(self.request, _('لطفاً خطاهای فرم اصلی و فرم‌ست‌ها را بررسی کنید'))
        return self.render_to_response(ctx)
class ProductUpdateView(ProductCreateView, UpdateView):
    def get_object(self):
        return get_object_or_404(Product, pk=self.kwargs['pk'], university=self.university)
class ProductSoftDeleteView(OffiMixin, View):
    def post(self, request, pk):
        prod = get_object_or_404(Product, pk=pk, university=self.university)
        prod.is_deleted = True; prod.save(update_fields=['is_deleted'])
        return JsonResponse({'status':'success','message':_('حذف نرم انجام شد'),'item_id':pk})
class ProductHardDeleteView(OffiMixin, View):
    def post(self, request, pk):
        prod = get_object_or_404(Product, pk=pk, university=self.university)
        prod.delete()
        return JsonResponse({'status':'success','message':_('حذف دائمی انجام شد'),'item_id':pk})

# Category
class CategoryListView(OffiMixin, ListView):
    model = ProductCategory
    template_name = 'unit_admin/categories/categories-list.html'
    context_object_name = 'rows'   # ما برای درخت دسته‌ها لیستی از (cat,level) پاس می‌دهیم
    paginate_by = 10



    def get_queryset(self):
        qs = ProductCategory.objects.filter(university=self.university)
        rows = build_category_tree(qs)
        # فیلتر جستجو
        q = self.request.GET.get('q', '').strip().lower()
        if q:
            rows = [(cat, lvl) for cat, lvl in rows if q in cat.title.lower()]
        return rows

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(
                self.request,
                'unit_admin/categories/_category_table.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)
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

#AdminSettings
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

# Contact
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

# BlogPost
class BlogPostListView(OffiMixin, ListView):
    model = BlogPost
    template_name = 'unit_admin/blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        qs = BlogPost.objects.filter(university=self.university)
        q = self.request.GET.get('q','').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        return qs.order_by('-published_at','-created_at')

    def render_to_response(self, context, **resp_kwargs):
        if self.request.GET.get('ajax') == '1':
            return render(self.request, 'unit_admin/blog/_post_rows.html', context)
        return super().render_to_response(context, **resp_kwargs)
class BlogPostCreateView(OffiMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'unit_admin/blog/post_form.html'
    success_url = reverse_lazy('unit_admin:blog_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.university = self.university
        # اگر منتشر شده و تاریخ نخورده، پرش کن
        if form.cleaned_data['is_published'] and not form.cleaned_data['published_at']:
            form.instance.published_at = timezone.now()
        messages.success(self.request, _('پست با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)
class BlogPostUpdateView(OffiMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = 'unit_admin/blog/post_form.html'
    success_url = reverse_lazy('unit_admin:blog_list')

    def get_object(self):
        return get_object_or_404(BlogPost, pk=self.kwargs['pk'], university=self.university)

    def form_valid(self, form):
        if form.cleaned_data['is_published'] and not form.cleaned_data['published_at']:
            form.instance.published_at = timezone.now()
        messages.success(self.request, _('تغییرات با موفقیت ذخیره شد'))
        return super().form_valid(form)
class BlogPostDeleteView(OffiMixin, View):
    """حذف دائمی با AJAX و JSON"""
    def post(self, request, pk):
        post = get_object_or_404(BlogPost, pk=pk, university=self.university)
        post.delete()
        return JsonResponse({'status':'success','message':_('پست حذف شد')})


class CommentListView(OffiMixin, ListView):
    model = Comment
    template_name = 'unit_admin/comments/comment_list.html'
    context_object_name = 'comments'
    paginate_by = 10

    def get_queryset(self):
        # فقط دیدگاه‌هایی که متعلق به دانشگاه همین دبیر واحد هستند
        qs = Comment.objects.select_related('user', 'content_type').order_by('-created_at')
        # فیلتر بر اساس دانشگاه
        qs = qs.filter(
            Q(content_type__model='blogpost', object_id__in=
                BlogPost.objects.filter(university=self.university).values_list('pk', flat=True)
            ) |
            Q(content_type__model='product', object_id__in=
                Product.objects.filter(university=self.university).values_list('pk', flat=True)
            )
        )
        # جستجو
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(content__icontains=q)
            )
        return qs

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # فقط ردیف‌های جدول
            return render(self.request, 'unit_admin/comments/_comment_rows.html', context)
        return super().render_to_response(context, **response_kwargs)


class CommentUpdateView(OffiMixin, UpdateView):
    model = Comment
    fields = ['content', 'is_approved']
    template_name = 'unit_admin/comments/comment_form.html'
    success_url = reverse_lazy('unit_admin:comment_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # اطمینان از این‌که تعلق به دانشگاه خودش باشد
        ct = obj.content_type.model
        if ct == 'blogpost':
            if obj.content_object.university != self.university:
                raise Http404
        # برای محصولات هم مشابه
        return obj


class CommentDeleteView(OffiMixin, DeleteView):
    model = Comment
    success_url = reverse_lazy('unit_admin:comment_list')
    template_name = 'unit_admin/comments/comment_confirm_delete.html'



class OrderListView(OffiMixin, ListView):
    model = Order
    template_name = 'unit_admin/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        qs = Order.objects.filter(
            items__product__university=self.university
        ).distinct().annotate(
            university_items_count=Sum('items__count', filter=Q(items__product__university=self.university)),
            university_total_price=Sum('items__total_price', filter=Q(items__product__university=self.university)),
        ).order_by('-created_at')

        q  = self.request.GET.get('q','').strip()
        f  = self.request.GET.get('from','').strip()
        t  = self.request.GET.get('to','').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q)
            )
        if f:
            qs = qs.filter(created_at__date__gte=f)
        if t:
            qs = qs.filter(created_at__date__lte=t)
        return qs

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('ajax') == '1':
            return render(self.request, 'unit_admin/orders/_order_rows.html', context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)


class OrderDetailView(OffiMixin, DetailView):
    model = Order
    template_name = 'unit_admin/orders/order_detail.html'
    context_object_name = 'order'

    def get_object(self):
        return get_object_or_404(
            Order,
            pk=self.kwargs['pk'],
            items__product__university=self.university
        )

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, _('وضعیت سفارش با موفقیت به‌روزرسانی شد.'))
        else:
            messages.error(request, _('وضعیت نامعتبر است.'))
        return redirect('unit_admin:order_detail', pk=order.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = ctx['order']
        items = order.items.filter(product__university=self.university)
        ctx['items'] = items
        # جمع مبلغ آیتم‌های دانشگاه جاری
        ctx['uni_total'] = items.aggregate(total=Sum('total_price'))['total'] or 0
        # وضعیت‌های قابل انتخاب
        ctx['status_choices'] = Order.STATUS_CHOICES
        # آدرس کامل
        if order.address:
            addr = order.address
            ctx['full_address'] = f"{addr.address}, {addr.city.name}، {addr.province.name} - کدپستی: {addr.postal_code}"
        else:
            ctx['full_address'] = _('بدون آدرس')
        return ctx


class OrderListReportPDFView(OffiMixin, View):
    def get(self, request, *args, **kwargs):
        # … your existing steps 1–4 …
        view = OrderListView()
        view.setup(request, *args, **kwargs)
        view.university = self.university
        orders = view.get_queryset()

        # → Compute totals
        total_items = sum(getattr(o, 'university_items_count', 0) for o in orders)
        total_price = sum(getattr(o, 'university_total_price', 0) for o in orders)

        # 5) render HTML
        html_string = render_to_string(
            'unit_admin/orders/report_list.html',
            {
              'orders': orders,
              'offi_university': self.university,
              'total_items': total_items,
              'total_price': total_price,
            }
        )

        # → rest of PDF generation unchanged …
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        css  = CSS(string='@page { size: A4; margin: 1cm }')
        pdf  = html.write_pdf(stylesheets=[css])

        filename = timezone.now().strftime("orders_report_%Y%m%d_%H%M.pdf")
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class OrderDetailReportPDFView(OffiMixin, View):
    def get(self, request, pk, *args, **kwargs):
        order = get_object_or_404(
            Order,
            pk=pk,
            items__product__university=self.university
        )
        items = order.items.filter(product__university=self.university)
        total = items.aggregate(sum=Sum('total_price'))['sum'] or 0

        html_string = render_to_string(
            'unit_admin/orders/report_detail.html',
            {
                'order': order,
                'items': items,
                'total': total,
                'offi_university': self.university
            }
        )
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        css = CSS(string='@page { size: A4; margin: 1cm }')
        pdf = html.write_pdf(stylesheets=[css])

        filename = timezone.now().strftime(f"order_{order.pk}_%Y%m%d_%H%M.pdf")
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response





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