# views.py
import secrets
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponseBadRequest
from .decorators import email_verified_required
from datetime import date
from django.contrib.auth import login
from django.http import Http404
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView,LogoutView,RedirectURLMixin
from django.views import View
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.generic import CreateView,UpdateView
from iranian_cities.models import Province, City
from university.models import University
from django.utils.translation import gettext_lazy as _
from .forms import (AddressForm,VerifyTokenForm,SignupForm,VerifiedAuthenticationForm, UserDashboardForm)
from .models import User, Membership, Address
import random
import logging
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.backends import ModelBackend
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from .forms import RequestRoleForm,ForgotPasswordForm, OTPForm, ResetPasswordForm
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from  utility.email_service import send_email
logger = logging.getLogger(__name__)

class SignupView(CreateView):
    model = User  # Add this line
    form_class = SignupForm
    template_name = "account/sign-up.html"
    success_url = reverse_lazy("login")
    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False  # کاربر در ابتدا غیر فعال است
        user.email_verified = False  # ایمیل تأیید نشده
        user.username = user.email  # نام کاربری برابر ایمیل قرار می‌دهیم
        print(f'User created with email: {user.email}')  # پرینت پس از ساخت کاربر
        user.save(using='default')

        # ایجاد کد تأیید ایمیل
        token = user.generate_email_verification_code()
        print(f'Generated email verification code: {token}')  # پرینت پس از ایجاد کد تأیید

        # ساخت URL تأیید ایمیل
        verification_url = self.request.build_absolute_uri(reverse_lazy('verify-email', kwargs={'pk': user.pk}))
        print(f'Verification URL: {verification_url}')  # پرینت URL تأیید

        # ارسال ایمیل از طریق تابع send_email
        try:
            send_email(
                subject='فعال سازی حساب کاربری',
                to=user.email,
                context={'user': user, 'verification_url': verification_url},
                template_name='account/email_verification.html'
            )
            print(f'Email sent successfully to {user.email}')  # پرینت پس از ارسال ایمیل
        except Exception as e:
            print(f'Failed to send email: {str(e)}')  # پرینت خطا در صورت ارسال نشدن ایمیل

        messages.info(self.request, _('کد تأیید به ایمیل شما ارسال شد'))
        return redirect('verify-email', pk=user.pk)


class VerifyEmailView(View):
    form_class = VerifyTokenForm
    template_name = 'account/verify-email.html'
    success_url = reverse_lazy('home')

    def get_user(self, pk):
        """Get unverified user or raise appropriate exception"""
        try:
            user = User.objects.get(pk=pk)
            if user.email_verified:
                logger.info(f"User {user.email} already verified")
                raise PermissionDenied("Already verified")
            return user
        except User.DoesNotExist:
            logger.error(f"User with pk {pk} not found")
            raise Http404

    def get(self, request, pk):
        try:
            user = self.get_user(pk)

            if user.is_verification_code_expired() or not user.email_verification_code:
                new_code = user.generate_email_verification_code()
                logger.info(f"Generated new code for {user.email}: {new_code}")
                messages.info(request, "کد جدید ارسال شد")

            return render(request, self.template_name, {
                'user': user,
                'form': self.form_class()
            })

        except PermissionDenied:
            messages.info(request, "حساب شما قبلاً تأیید شده است")
            return redirect(self.success_url)
        except Http404:
            messages.error(request, "حساب کاربری یافت نشد")
            return redirect('signup')

    def post(self, request, pk):
        try:
            user = self.get_user(pk)
            form = self.form_class(request.POST)

            if not form.is_valid():
                return render(request, self.template_name, {'user': user, 'form': form})

            entered_code = form.cleaned_data['token'].strip()

            # Code verification
            if user.email_verification_code != entered_code:
                logger.warning(f"Invalid code entered for {user.email}")
                messages.error(request, "کد وارد شده اشتباه است")
                return render(request, self.template_name, {'user': user, 'form': form})

            # Expiration check
            if user.is_verification_code_expired():
                logger.warning(f"Expired code used for {user.email}")
                messages.error(request, "کد وارد شده منقضی شده است")
                return redirect('verify-email', pk=pk)

            # Verification process
            user.email_verified = True
            user.clear_verification_code()
            user.save(update_fields=['email_verified', 'email_verification_code', 'email_verification_code_created'])

            # Login user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            logger.info(f"Successfully verified {user.email}")

            messages.success(request, "تأیید ایمیل با موفقیت انجام شد!")
            return redirect(self.success_url)

        except PermissionDenied:
            messages.info(request, "حساب شما قبلاً تأیید شده است")
            return redirect(self.success_url)
        except Http404:
            messages.error(request, "حساب کاربری یافت نشد")
            return redirect('signup')
        except Exception as e:
            logger.error(f"Verification failed for {pk}: {str(e)}", exc_info=True)
            messages.error(request, "خطای سیستمی موقت رخ داده است. لطفاً مجدداً تلاش کنید")
            return redirect('verify-email', pk=pk)  # Stay on verification page

@method_decorator(ratelimit(key='ip', rate='3/h'), name='dispatch')
class ResendVerificationView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if not user.email_verified:
            # تولید کد جدید فقط اگر کاربر تایید نشده باشد
            code = user.generate_email_verification_code()  # تغییر نام متد
            print(f"\n=== NEW RESEND CODE ===\n{code}\n")

            # ارسال ایمیل
            subject = 'کد تأیید جدید'
            html_message = render_to_string('account/email_verification.html', {
                'code': code,  # استفاده مستقیم از کد ۶ رقمی
                'user': user
            })
            send_mail(
                subject,
                strip_tags(html_message),
                'noreply@azadshop.ir',
                [user.email],
                html_message=html_message
            )
            messages.success(request, "کد جدید ارسال شد!")

        return redirect('verify-email', pk=user.pk)

class CustomLoginView(LoginView):
    template_name = "account/login.html"
    authentication_form = VerifiedAuthenticationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, _("شما قبلاً وارد سیستم شده‌اید. در حال انتقال به پیشخوان..."))
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        # Reset security counters
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])

        messages.success(self.request, _("شما با موفقیت وارد شدید."))
        return super().form_valid(form)

    def form_invalid(self, form):
        # Handle locked accounts
        for error in form.non_field_errors().as_data():
            if error.code == 'account_locked':
                return self.response_class(
                    request=self.request,
                    template=self.template_name,
                    context=self.get_context_data(form=form),
                    using=self.template_engine
                )

        # General error handling
        messages.error(self.request, _("مشکلی در ورود به سیستم رخ داده است. لطفاً اطلاعات خود را بررسی کنید."))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "redirect_to": self.get_redirect_url(),
            "breadcrumb": [
                {"name": _("حساب کاربری"), "url": reverse_lazy("login")},
                {"name": _("ورود"), "url": ""},
            ],
            "breadcrumb_title": _("حساب کاربری : ورود")
        })
        return context

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, _("شما با موفقیت خارج شدید."))
        return super().dispatch(request, *args, **kwargs)

@method_decorator(ratelimit(key='post:username', rate='5/h'), name='post')
class ForgotPasswordView(FormView):
    template_name = "account/forgot_password_email.html"
    form_class = ForgotPasswordForm
    success_url = reverse_lazy("verify_otp")

    def form_valid(self, form):
        email = form.cleaned_data["username"]
        user = User.objects.filter(email=email).first()
        if not user:
            form.add_error("username", _("حسابی با این ایمیل یافت نشد."))
            return self.form_invalid(form)

        user.otp_secret = str(random.randint(100000, 999999))
        user.save(update_fields=["otp_secret"])
        self.request.session["forgot_email"] = email
        messages.success(self.request, _("کد بازیابی به ایمیل شما ارسال شد."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumb"] = [
            {"name": _("حساب کاربری"), "url": reverse_lazy("login")},
            {"name": _("فراموشی رمز عبور"), "url": ""},
        ]
        ctx["breadcrumb_title"] = _("حساب کاربری : فراموشی رمز عبور")
        return ctx

class VerifyOTPView(FormView):
    template_name = "account/verify_otp.html"
    form_class = OTPForm
    success_url = reverse_lazy("reset_password")

    def form_valid(self, form):
        otp_input = form.cleaned_data["otp_code"]
        email = self.request.session.get("forgot_email")
        user = User.objects.filter(email=email).first()
        if not user or user.otp_secret != otp_input:
            form.add_error("otp_code", _("کد وارد شده صحیح نمی‌باشد."))
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumb"] = [
            {"name": _("حساب کاربری"), "url": reverse_lazy("login")},
            {"name": _("تأیید کد بازیابی"), "url": ""},
        ]
        ctx["breadcrumb_title"] = _("حساب کاربری : تأیید کد بازیابی")
        return ctx


class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = "account/change_password.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy("user_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "breadcrumb": [
                {"name": _("حساب کاربری"), "url": reverse_lazy("user_dashboard")},
                {"name": _("تغییر رمز عبور"), "url": ""},
            ],
            "breadcrumb_title": _("حساب کاربری : تغییر رمز عبور")
        })
        return context

class ResetPasswordView(FormView):
    template_name = "account/reset_password.html"
    form_class = ResetPasswordForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        pwd = form.cleaned_data["new_password"]
        cpwd = form.cleaned_data["confirm_password"]
        email = self.request.session.get("forgot_email")
        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(self.request, _("حساب کاربری یافت نشد."))
            return redirect("forgot_password")
        if pwd != cpwd:
            form.add_error("confirm_password", _("رمز عبور و تکرار آن مطابقت ندارند."))
            return self.form_invalid(form)

        user.set_password(pwd)
        user.otp_secret = ""
        user.save(update_fields=["password", "otp_secret"])
        messages.success(
            self.request,
            _("رمز عبور با موفقیت تغییر یافت. لطفاً وارد شوید."),
        )
        self.request.session.pop("forgot_email", None)
        return super().form_valid(form)
    def get(self, request, *args, **kwargs):
        if not request.session.get('forgot_email'):
            raise PermissionDenied
        return super().get(request, *args, **kwargs)
    # def get_context_data(self, **kwargs):
    #     ctx = super().get_context_data(**kwargs)
    #     ctx["breadcrumb"] = [
    #         {"name": _("حساب کاربری"), "url": reverse_lazy("login")},
    #         {"name": _("تغییر رمز عبور"), "url": ""},
    #     ]
    #     ctx["breadcrumb_title"] = _("حساب کاربری : تغییر رمز عبور")
    #     return ctx


class UserDashboardView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserDashboardForm
    template_name = "account/user-dashboard.html"
    success_url = reverse_lazy("user_dashboard")
    login_url = reverse_lazy('login')

    def get_object(self, queryset=None):
        return self.request.user

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        # Handle avatar upload separately
        if 'avatar' in request.FILES:
            if request.FILES['avatar'].size > 2 * 1024 * 1024:
                messages.error(request, _("حجم تصویر نباید بیشتر از ۲ مگابایت باشد"))
                return redirect(self.success_url)

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _("تغییرات با موفقیت ذخیره شد"))
            return response
        except IntegrityError as e:
            messages.error(self.request, _("خطا در ذخیره اطلاعات. اطلاعات تکراری وجود دارد"))
            return self.form_invalid(form)
        except ValidationError as e:
            messages.error(self.request, _("خطا در داده‌های ورودی: %s") % e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("لطفاً خطاهای زیر را اصلاح کنید"))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object  # Use the view's object instead of request.user
        list_address = Address.objects.filter(user=user)

        # Basic user information
        context.update({
            "full_name": user.get_full_name() or user.username,
            "email": user.email,
            "location": self._get_user_location(user),
            "activity_years": self._calculate_activity_years(user),
            "national_code": user.national_code,
            "birthday": user.birthday,
            "phone": user.mobile,
            "confirmed_memberships":user.memberships.filter(is_confirmed=True),
            "address": user.address,
            "list_addresses": list_address,
            "postal_code": user.postal_code,
            "memberships": self._get_user_memberships(user),
            "address_form": AddressForm(),
            "address_forms": self._get_address_forms(user),
            "universities": University.objects.only("id", "name"),
            "provinces": Province.objects.only("id", "name"),
            "cities": City.objects.only("id", "name"),
            "breadcrumb": [
                {"name": _("حساب کاربری"), "url": reverse_lazy("user_dashboard")},
                {"name": _("داشبورد"), "url": ""},
            ],
            "breadcrumb_title": _("حساب کاربری : داشبورد")
        })

        return context

    def _get_user_location(self, user):
        """Format province and city information"""
        location_parts = []
        if user.province:
            location_parts.append(user.province.name)
        if user.city:
            location_parts.append(user.city.name)
        return "، ".join(location_parts) if location_parts else _("ثبت نشده")

    def _calculate_activity_years(self, user):
        """Calculate user's account age"""
        if user.date_joined:
            delta = date.today() - user.date_joined.date()
            return delta.days // 365
        return 0

    def _get_user_memberships(self, user):
        """Get membership data based on user role"""
        if Membership.objects.filter(
                user=user,
                role=Membership.Role.UNIT_OFFICER,
                is_confirmed=True
        ).exists():
            return Membership.objects.filter(
                is_confirmed=True,
                university__city=user.city
            ).select_related("university", "user")
        return user.memberships.filter(
            is_confirmed=True
        ).select_related("university")

    def _get_address_forms(self, user):
        """Generate address forms for existing addresses"""
        return {
            addr.id: AddressForm(instance=addr)
            for addr in user.addresses.all()
        }

class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    # We won’t use a separate template; we’ll post back to the dashboard
    success_url = reverse_lazy('user_dashboard')

    def get_queryset(self):
        # Ensure users can only edit their own addresses
        return super().get_queryset().filter(user=self.request.user)

class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    success_url = reverse_lazy('user_dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class AddressSetDefaultView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # clear old default
        Address.objects.filter(user=request.user, active=True).update(active=False)
        # set new default
        addr = get_object_or_404(Address, pk=pk, user=request.user)
        addr.active = True
        addr.save(update_fields=['active'])
        return redirect('user_dashboard')

class RequestRoleView(LoginRequiredMixin, FormView):
    template_name = 'account/request_role.html'
    form_class    = RequestRoleForm
    success_url   = reverse_lazy('user_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.access_level < User.Level.PROFILE_COMPLETED:
            messages.error(request, _("لطفا ابتدا اطلاعات پروفایل خود را کامل کنید."))
            return redirect('user_dashboard')
        return super().dispatch(request, *args, **kwargs)
    def form_valid(self, form):
        m, created = Membership.objects.get_or_create(
            user=self.request.user,
            university=form.cleaned_data['university'],
            role=form.cleaned_data['role'],
            defaults={'code': form.cleaned_data['code']}
        )
        if not created:
            messages.warning(self.request, _("شما قبلا برای این نقش درخواست داده‌اید."))
        else:
            messages.success(self.request, _("درخواست شما ثبت شد؛ منتظر تایید مدیر باشید."))
        return super().form_valid(form)

class LevelRequiredMixin:
    """
    Mixin to enforce a minimum access_level on class-based views.
    usage: subclass and set "min_level = User.Level.PROFILE_COMPLETED"
    """
    in_level = User.Level.EMAIL_CONFIRMED

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect('login')
        if user.access_level < self.min_level:
            messages.warning(request, _("برای دسترسی به این بخش باید ابتدا سطح دسترسی خود را ارتقا دهید."))
            # redirect to dashboard or a custom page
            return redirect('user_dashboard')
        return super().dispatch(request, *args, **kwargs)

class ProfileSettingsView(LoginRequiredMixin, LevelRequiredMixin, UpdateView):
    min_level = User.Level.PROFILE_COMPLETED
    model = User
    form_class = UserDashboardForm
    template_name = 'account/user-dashboard.html'

    def get_object(self):
        return self.request.user

class AccountLockoutView(View):
    template_name = 'account/lockout.html'

    def get(self, request):
        user = request.user
        return render(request, self.template_name, {
            'locked_until': user.locked_until if user.is_authenticated else None
        })