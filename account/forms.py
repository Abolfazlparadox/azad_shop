# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User, Membership, Address
from iranian_cities.models import Province, City
from university.models import University
from django.urls import reverse
from django.utils.html import format_html
from django.core.validators import RegexValidator, FileExtensionValidator


import logging
logger = logging.getLogger(__name__)

def validate_file_size(value):
    limit = 2 * 1024 * 1024  # 2MB
    if value.size > limit:
        raise ValidationError(_('حجم فایل نباید بیشتر از ۲ مگابایت باشد'))

class SignupForm(UserCreationForm):
    fullname = forms.CharField(
        label=_("نام و نام خانوادگی"),
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': _('نام و نام خانوادگی'), 'class': 'form-control'})
    )
    terms_accepted = forms.BooleanField(
        label=_("شرایط و قوانین را می‌پذیرم"),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        # include the two password fields from UserCreationForm
        fields = ['fullname', 'email', 'password1', 'password2', 'terms_accepted']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('آدرس ایمیل خود را وارد کنید')
            }),
        }

    def clean_fullname(self):
        fullname = self.cleaned_data['fullname'].strip()
        if len(fullname.split()) < 2:
            raise forms.ValidationError(_("لطفا نام و نام خانوادگی را به صورت کامل وارد کنید"))
        return fullname

    def save(self, commit=True):
        user = super().save(commit=False)
        # split fullname into first/last
        first, *rest = self.cleaned_data['fullname'].split(maxsplit=1)
        user.first_name = first
        user.last_name = rest[0] if rest else ''
        user.username = self.cleaned_data['email']
        # role and other defaults
        user.role = 'CUST'
        if commit:
            user.save()
        return user


class VerifyTokenForm(forms.Form):
    token = forms.CharField(
        label=_("کد تأیید"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123456',
            'inputmode': 'numeric',
            'pattern': '\d*'  # Only numbers allowed
        }),
        error_messages={
            'required': 'لطفا کد تأیید را وارد کنید',
            'min_length': 'کد باید دقیقا ۶ رقم باشد',
            'max_length': 'کد باید دقیقا ۶ رقم باشد'
        }
    )


class VerifiedAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("آدرس ایمیل"),
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': _('example@domain.com'),
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        label=_("رمز عبور"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': _('رمز عبور خود را وارد کنید'),
            'autocomplete': 'current-password'
        })
    )

    error_messages = {
        'invalid_login': _("ایمیل یا رمز عبور صحیح نیست."),
        'inactive': _("این حساب کاربری غیرفعال شده است."),
        'unregistered_email': _("این ایمیل در سیستم ثبت نشده است."),
        'account_locked': _("حساب شما به دلیل تلاش‌های مکرر ناموفق به مدت %(minutes)d دقیقه قفل شده است."),
        'email_not_verified': _("لطفاً ابتدا ایمیل خود را تأیید کنید.")
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.is_locked:
            remaining = (user.locked_until - timezone.now()).total_seconds() // 60
            raise ValidationError(
                self.error_messages['account_locked'],
                code='account_locked',
                params={'minutes': int(remaining)}
            )

        if not user.email_verified:
            self.request.session['unverified_user_id'] = user.pk
            verify_url = reverse('verify-email', kwargs={'pk': user.pk})
            message = format_html(
                _('حساب شما فعال است اما ایمیل تأیید نشده. برای تأیید <a href="{url}">اینجا کلیک کنید</a>'),
                url=verify_url
            )
            raise ValidationError(message, code='email_not_verified')

    def clean(self):
        try:
            # Let parent handle basic validation
            return super().clean()
        except ValidationError as e:
            # Handle our custom errors
            if hasattr(e, 'code') and e.code in ('account_locked', 'email_not_verified'):
                raise

            # Handle failed login attempts
            user = self.get_user()
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = timezone.now() + timezone.timedelta(minutes=15)
                user.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("آدرس ایمیل"),
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': _('آدرس ایمیل خود را وارد کنید'),
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        label=_("رمز عبور"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': _('رمز عبور خود را وارد کنید'),
            'autocomplete': 'current-password'
        })
    )

    error_messages = {
        'invalid_login': _("ایمیل یا رمز عبور صحیح نیست."),
        'inactive': _("این حساب کاربری غیرفعال شده است."),
        'unregistered_email': _("این ایمیل در سیستم ثبت نشده است.")
    }

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # First check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError(
                self.error_messages['unregistered_email'],
                code='unregistered_email'
            )

        # Then validate credentials
        if user and not user.check_password(password):
            raise ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login'
            )

        # Finally check for active status
        if not user.is_active:
            raise ValidationError(
                self.error_messages['inactive'],
                code='inactive'
            )

        return self.cleaned_data

class RequestRoleForm(forms.ModelForm):
    university = forms.ModelChoiceField(
        label=_("دانشگاه"),
        queryset=University.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': _('دانشگاه خود را انتخاب کنید')
        })
    )
    role = forms.ChoiceField(
        label=_("نقش"),
        choices=Membership.Role,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': _('نقش مورد نظر را انتخاب کنید')
        })
    )
    code = forms.CharField(
        label=_("کد احراز هویت"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('کد دریافتی از دانشگاه را وارد کنید')
        })
    )

    error_messages = {
        'invalid_code': _("کد وارد شده معتبر نیست."),
        'existing_membership': _("شما قبلاً برای این دانشگاه درخواست داده‌اید."),
        'role_mismatch': _("کد وارد شده با نقش انتخابی مطابقت ندارد."),
        'university_inactive': _("این دانشگاه در حال حاضر فعال نیست."),
    }

    class Meta:
        model = Membership
        fields = ['university', 'role', 'code']

    def clean_university(self):
        university = self.cleaned_data.get('university')
        if not university.is_active:
            raise forms.ValidationError(
                self.error_messages['university_inactive'],
                code='university_inactive'
            )
        return university

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if len(code) != 8:  # Example validation
            raise forms.ValidationError(
                self.error_messages['invalid_code'],
                code='invalid_code'
            )
        return code

    def clean(self):
        cleaned_data = super().clean()
        university = cleaned_data.get('university')
        role = cleaned_data.get('role')
        code = cleaned_data.get('code')

        # Check for existing membership
        if Membership.objects.filter(
            user=self.instance.user,
            university=university
        ).exists():
            raise forms.ValidationError(
                self.error_messages['existing_membership'],
                code='existing_membership'
            )

        # Validate code against university and role
        if not self.validate_verification_code(university, role, code):
            raise forms.ValidationError(
                self.error_messages['role_mismatch'],
                code='role_mismatch'
            )

        return cleaned_data

    def validate_verification_code(self, university, role, code):
        """
        Custom validation logic for verification codes
        """
        # Implement your actual code validation logic here
        # Example: Check code against university's verification system
        return len(code) == 8  # Replace with real validation

    def save(self, commit=True):
        membership = super().save(commit=False)
        membership.user = self.instance.user
        membership.is_confirmed = False
        if commit:
            membership.save()
        return membership

class ForgotPasswordForm(forms.Form):
    username = forms.EmailField(
        label=_("ایمیل"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('ایمیل خود را وارد کنید')
        })
    )

class OTPForm(forms.Form):
    otp_code = forms.CharField(
        label=_("کد بازیابی"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('کد بازیابی را وارد کنید')
        })
    )

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label=_("رمز جدید"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('رمز جدید')
        })
    )
    confirm_password = forms.CharField(
        label=_("تکرار رمز جدید"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('تکرار رمز جدید')
        })
    )

class UserDashboardForm(forms.ModelForm):
    first_name = forms.CharField(
        label=_("نام"),
        required=True,
        help_text=_("نام خود را وارد کنید"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('نام خود را وارد کنید'),
        }),
        error_messages={'required': _("وارد کردن نام الزامی است.")}
    )
    last_name = forms.CharField(
        label=_("نام خانوادگی"),
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('نام خانوادگی خود را وارد کنید'),
        }),
        error_messages={'required': _("وارد کردن نام خانوادگی الزامی است.")}
    )
    email = forms.EmailField(
        label=_("ایمیل"),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('آدرس ایمیل خود را وارد کنید'),
        }),
        error_messages={
            'required': _("وارد کردن ایمیل الزامی است."),
            'invalid': _("فرمت ایمیل صحیح نیست.")
        }
    )
    national_code = forms.CharField(
        label=_("کد ملی"),
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('کد ملی 10 رقمی'),
            'maxlength': 10,
        }),
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message=_("کد ملی باید 10 رقم باشد")
            )
        ],
        error_messages={'required': _("وارد کردن کد ملی الزامی است.")}
    )
    birthday = forms.DateField(
        label=_("تاریخ تولد"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    province = forms.ModelChoiceField(
        label=_("استان"),
        queryset=Province.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.ModelChoiceField(
        label=_("شهر"),
        queryset=City.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    university = forms.ModelChoiceField(
        label=_("دانشگاه"),
        queryset=University.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        label=_("آدرس دقیق"),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('آدرس کامل خود را وارد کنید'),
        })
    )
    postal_code = forms.CharField(
        label=_("کد پستی"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('کد پستی'),
            'maxlength': 10,
        })
    )
    mobile = forms.CharField(
        label=_("شماره موبایل"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('09xxxxxxxxx'),
            'maxlength': 11,
        }),
        validators=[
            RegexValidator(
                regex=r'^(\+98|0)?9\d{9}$',
                message=_("شماره موبایل باید با 09 شروع شود و ۱۱ رقم باشد")
            )
        ]
    )
    avatar = forms.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', 'webp']),
            validate_file_size  # Custom validator
        ]
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 'national_code',
            'birthday', 'avatar', 'province', 'city', 'university',
            'address', 'postal_code',
        ]

    def clean_national_code(self):
        national_code = self.cleaned_data['national_code']
        if User.objects.filter(national_code=national_code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("این کد ملی قبلاً ثبت شده است"))
        return national_code

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        # Normalize phone number format
        if mobile.startswith('0'):
            mobile = '+98' + mobile[1:]
        elif not mobile.startswith('+98'):
            mobile = '+98' + mobile

        if User.objects.filter(mobile=mobile).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("این شماره موبایل قبلاً ثبت شده است"))
        return mobile

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'name', 'category', 'address',
            'postal_code', 'telephone', 'province',
            'city', 'active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('عنوان نشانی خود را وارد کنید'),
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('آدرس کامل خود را وارد کنید'),
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('کد پستی خود را وارد کنید'),
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('شماره تماس خود را وارد کنید'),
            }),
            'province': forms.Select(attrs={
                'class': 'form-select',
            }),
            'city': forms.Select(attrs={
                'class': 'form-select',
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }