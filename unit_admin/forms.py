# unit_admin/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from iranian_cities.models import Province, City
from account.models import User, Membership
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomAdminAuthForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )


class RoleCreationForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="کاربر",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        choices=Membership.Role.choices,
        label="نقش",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    code = forms.CharField(
        label="کد نقش",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Membership
        fields = ['user', 'role', 'code']

    def __init__(self, *args, **kwargs):
        # 1) Pop our custom kwargs
        current_user = kwargs.pop('current_user', None)
        self.university = kwargs.pop('university', None)

        # 2) Call parent
        super().__init__(*args, **kwargs)

        # 3) Build user queryset: exclude superusers, OFFI-role, self
        qs = User.objects.all().exclude(is_superuser=True)
        qs = qs.exclude(memberships__role='OFFI')
        if current_user:
            qs = qs.exclude(pk=current_user.pk)
        self.fields['user'].queryset = qs.distinct()

        # 4) Remove OFFI from role choices
        self.fields['role'].choices = [
            (v, l) for v, l in Membership.Role.choices
            if v != 'OFFI'
        ]

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get('user')
        role = cleaned.get('role')
        # now self.university is set
        if user and role and self.university:
            exists = Membership.objects.filter(
                user=user,
                role=role,
                university=self.university
            ).exists()
            if exists:
                raise forms.ValidationError("این کاربر قبلاً این نقش را در دانشگاه شما دارد")
        return cleaned

class CustomUserCreationForm(UserCreationForm):
    province = forms.ModelChoiceField(
        queryset=Province.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select',
                                   'data-control': 'province-select'})
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select',
                                   'data-control': 'city-select'})
    )

    class Meta:
        model = User
        fields = (
            'username', 'password1','email', 'password2', 'first_name', 'last_name',
            'mobile', 'national_code', 'birthday', 'avatar', 'province', 'city',
            'address', 'postal_code', 'is_verified', 'is_staff', 'is_active',
            'marketing_consent', 'terms_accepted', 'email_verified'
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کاربری خود را وارد کنید'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'رمز عبور را وارد کنید',
                'autocomplete': 'new-password'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ایمیل خود را وارد کنید'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'تکرار رمز عبور',
                'autocomplete': 'new-password'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خانوادگی'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '۰۹۱۲۳۴۵۶۷۸۹',
                'type': 'tel'
            }),
            'national_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد ملی (۱۰ رقم)',
                'maxlength': '10'
            }),
            'birthday': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'avatar': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),

            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'خیابان، پلاک، واحد',
                'rows': 3
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد پستی ۱۰ رقمی',
                'maxlength': '10'
            }),
            'is_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'marketing_consent': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'terms_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'email_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            })
        }

    def __init__(self, *args, **kwargs):
        # دریافت دانشگاه از پارامترهای ورودی
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        # تنظیمات اولیه برای شهرها
        self.fields['city'].queryset = City.objects.none()

        # اگر استان از قبل انتخاب شده بود
        if 'province' in self.data:
            try:
                province_id = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=province_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['city'].queryset = self.instance.province.city_set.all()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است")
        return email

    def clean_birthday(self):
        birthday = self.cleaned_data.get('birthday')
        if birthday and birthday > timezone.now().date():
            raise forms.ValidationError("تاریخ تولد نمی‌تواند در آینده باشد")
        return birthday

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if User.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError("این شماره موبایل قبلاً ثبت شده است")
        return mobile

    def clean_national_code(self):
        national_code = self.cleaned_data.get('national_code')
        if User.objects.filter(national_code=national_code).exists():
            raise forms.ValidationError("این کد ملی قبلاً ثبت شده است")
        return national_code

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # ایجاد عضویت برای کاربر در دانشگاه مربوطه
            Membership.objects.create(
                user=user,
                university=self.university,  # استفاده از دانشگاه دریافتی
                role='student',  # نقش پیش‌فرض
                is_confirmed=True
            )
        return user