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

from product.models import Product,ProductCategory
from unit_admin.forms import CustomUserCreationForm, RoleCreationForm, AddressForm, ProductForm
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest

User = get_user_model()

class UnitAdminIndexView(LoginRequiredMixin, TemplateView):
    """
    نمایش داشبورد پنل مدیریت دبیر رفاهی
    تنها کاربرانی با نقش OFFI و عضویت تأییدشده در دانشگاه اجازه‌دسترسی دارند.
    """
    template_name = 'unit_admin/index.html'
    login_url = 'login'       # adjust if your login URL name differs
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        # 1) کاربر وارد نشده → هدایت به صفحه لاگین
        # (handled by LoginRequiredMixin)

        # 2) چک دسترسی OFFI
      if request.user.is_authenticated:
        if not request.user.memberships.filter(role='OFFI', is_confirmed=True).exists():
            raise PermissionDenied("شما دسترسی لازم را ندارید")
      else:
          raise PermissionDenied("شما دسترسی لازم را ندارید")
      return super().dispatch(request, *args, **kwargs)



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


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "unit_admin/users/all-users.html"
    context_object_name = "users"
    paginate_by = 3

    def get_queryset(self):
        try:
            admin_membership = self.request.user.memberships.get(role='OFFI')
            university = admin_membership.university
            return User.objects.filter(
                memberships__university=university,
                memberships__is_confirmed=True
            ).exclude(id=self.request.user.id).distinct()
        except Membership.DoesNotExist:
            raise PermissionDenied("Access denied.")
class UserCreateView(LoginRequiredMixin, CreateView):
    form_class = CustomUserCreationForm
    template_name = "unit_admin/users/add-new-user.html"

    def get_success_url(self):
        return reverse_lazy('unit_admin:user_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['university'] = self.request.user.memberships.get(role='OFFI').university

        except Membership.DoesNotExist:
            raise PermissionDenied("شما دسترسی لازم را ندارید")
        return kwargs

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
class UserDeleteView(LoginRequiredMixin, View):
    """
    Handles AJAX (and normal) POST to delete a user.
    """

    def post(self, request, pk, *args, **kwargs):
        # Permission check
        if not request.user.memberships.filter(role='OFFI', is_confirmed=True).exists():
            raise PermissionDenied("شما دسترسی لازم را ندارید")

        target = get_object_or_404(User, pk=pk)

        if target == request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'نمی‌توانید کاربر فعلی را حذف کنید'
            }, status=400)

        target.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})

        messages.success(request, "کاربر با موفقیت حذف شد")
        return redirect('user_list')
class UserUpdateView(UpdateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'unit_admin/users/add-new-user.html'
    context_object_name = 'user_obj'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        kwargs['university']   = self.request.user.memberships.get(role='OFFI').university
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('اطلاعات کاربر با موفقیت به‌روز شد'))
        return redirect('unit_admin:user_list')

    def form_invalid(self, form):
        print('hi')
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید'))
        return self.render_to_response(self.get_context_data(form=form))

#city:
def get_cities(request):
    province_id = request.GET.get('province_id')

    if not province_id:
        return  HttpResponseBadRequest("پارامتر province_id الزامی است")

    try:
        cities = City.objects.filter(province_id=province_id)
    except City.DoesNotExist:
        cities = []

    return render(request, 'unit_admin/includes/city_options.html', {'cities': cities})
#role

class RoleListView(LoginRequiredMixin, ListView):
    model = Membership
    template_name = "unit_admin/roles/all-roll.html"
    context_object_name = "memberships"
    paginate_by = 10

    def get_queryset(self):
        try:
            university = self.request.user.memberships.get(role='OFFI').university
            return Membership.objects.filter(
                university=university
            ).exclude(user=self.request.user).distinct()
        except Membership.DoesNotExist:
            raise PermissionDenied("Access denied.")
class RoleCreateView(LoginRequiredMixin, CreateView):
    form_class    = RoleCreationForm
    template_name = "unit_admin/roles/add-new-roll.html"
    success_url   = reverse_lazy('unit_admin:role_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # pass current user
        kwargs['current_user'] = self.request.user
        # pass university for form validation
        kwargs['university']   = self.request.user.memberships.get(role='OFFI').university
        return kwargs

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
class RoleDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        role_id = request.POST.get('role_id')
        try:
            university = request.user.memberships.get(role='OFFI').university
            membership = get_object_or_404(Membership, id=role_id, university=university)
            membership.delete()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Role deleted successfully.'})
            messages.success(request, "Role deleted successfully.")
        except Membership.DoesNotExist:
            messages.error(request, "Role not found.")
        return redirect('unit_admin:role_list')
class RoleUpdateView(UpdateView):
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

#address

class AddressMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        try:
            offi = request.user.memberships.get(role='OFFI', is_confirmed=True)
        except Membership.DoesNotExist:
            raise PermissionDenied(_('شما دسترسی لازم را ندارید'))
        self.university = offi.university
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kws = super().get_form_kwargs()
        kws['university'] = self.university
        return kws

class AddressListView(AddressMixin, ListView):
    model = Address
    template_name = 'unit_admin/addresses/address_list.html'
    context_object_name = 'addresses'
    paginate_by = 10

class AddressCreateView(AddressMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'unit_admin/addresses/address_form.html'
    success_url = reverse_lazy('unit_admin:address_list')

    def form_valid(self, form):
        messages.success(self.request, _('نشانی با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)

class AddressUpdateView(AddressMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'unit_admin/addresses/address_form.html'
    success_url = reverse_lazy('unit_admin:address_list')

    def get_object(self, queryset=None):
        return get_object_or_404(
            Address.objects.filter(
                user__memberships__university=self.university,
                user__memberships__is_confirmed=True
            ), pk=self.kwargs['pk']
        )

    def form_valid(self, form):
        messages.success(self.request, _('نشانی با موفقیت بروزرسانی شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در بروزرسانی نشانی'))
        return super().form_invalid(form)
class AddressDeleteView(AddressMixin, DeleteView):
    model         = Address
    template_name = 'unit_admin/addresses/address_list.html'
    success_url   = reverse_lazy('unit_admin:address_list')

    def get_object(self, queryset=None):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        messages.success(self.request, _('نشانی با موفقیت حذف شد'))
        return super().delete(request, *args, **kwargs)

#product
class OffiProductMixin:
    """Ensure OFFI access and set `self.university`."""
    def dispatch(self, request, *args, **kwargs):
        try:
            offi = request.user.memberships.get(role='OFFI', is_confirmed=True)
        except Membership.DoesNotExist:
            raise PermissionDenied(_('شما دسترسی لازم را ندارید'))
        self.university = offi.university
        return super().dispatch(request, *args, **kwargs)

class ProductListView(LoginRequiredMixin, OffiProductMixin, ListView):
    model = Product
    template_name = 'unit_admin/products/products.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        return Product.objects.filter(
            university=self.university,
        ).order_by('-created_at')

class ProductCreateView(LoginRequiredMixin, OffiProductMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'unit_admin/products/product_form.html'
    success_url = reverse_lazy('unit_admin:product_list')

    def form_valid(self, form):
        form.instance.university = self.university
        messages.success(self.request, _('محصول با موفقیت ایجاد شد'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را اصلاح کنید'))
        return super().form_invalid(form)

class ProductSoftDeleteView(LoginRequiredMixin, OffiProductMixin, View):
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

class ProductHardDeleteView(LoginRequiredMixin, OffiProductMixin, DeleteView):
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

# Individual Mixins
class CategoriesMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class OrdersMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class SettingsMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class TaxMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class TicketsMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class ReportsMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


# Views
class CategoriesListView(CategoriesMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/categories/list.html"
    context_object_name = 'categories'
    ordering = ['-name']
    paginate_by = 20

class OrdersListView(OrdersMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/orders/list.html"
    context_object_name = 'orders'
    ordering = ['-created_at']
    paginate_by = 15

class SettingsListView(SettingsMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/settings/list.html"
    context_object_name = 'settings'

class TaxListView(TaxMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/tax/list.html"
    context_object_name = 'taxes'
    ordering = ['-rate']

class TicketsListView(TicketsMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/tickets/list.html"
    context_object_name = 'tickets'
    ordering = ['-created_at']

class ReportsListView(ReportsMixin, ListView):
    model = ProductCategory  # Replace with your actual model
    template_name = "unit_admin/reports/list.html"
    context_object_name = 'reports'
    ordering = ['-generated_at']