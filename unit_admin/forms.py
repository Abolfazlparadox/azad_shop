# unit_admin/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.utils import timezone
from iranian_cities.models import Province, City
from account.models import User, Membership, AdminActionLog
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

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
        self.current_user = kwargs.pop('current_user', None)
        self.university = kwargs.pop('university', None)

        # 2) Call parent
        super().__init__(*args, **kwargs)

        # 3) Build user queryset: exclude superusers, OFFI-role, self
        qs = User.objects.all().exclude(is_superuser=True)
        qs = qs.exclude(memberships__role='OFFI')
        if self.current_user:
            qs = qs.exclude(pk=self.current_user.pk)
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

    def save(self, commit=True):
        with transaction.atomic():
            membership = super().save(commit=commit)
            membership.university = self.university
            membership.is_confirmed = True
            membership.confirmed_at = timezone.now()
            membership.save()
            AdminActionLog.objects.create(
                actor=self.current_user,
                action='create_role',
                target_role=membership,
                metadata={
                    'role': membership.role,
                    'university': str(self.university)
                }
            )
        return membership

# unit_admin/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.utils import timezone

from iranian_cities.models import Province, City
from account.models import User, Membership, AdminActionLog


class CustomUserCreationForm(UserCreationForm):
    province = forms.ModelChoiceField(
        queryset=Province.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-control': 'province-select'
        })
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.none(),  # start empty; set in __init__
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-control': 'city-select'
        })
    )

    class Meta:
        model = User
        fields = (
            'username',   'password1',      'email',     'password2',
            'first_name', 'last_name',      'mobile',    'national_code',
            'birthday',   'avatar',         'province',  'city',
            'address',    'postal_code',    'is_verified',
            'is_staff',   'is_active',      'marketing_consent',
            'terms_accepted','email_verified'
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('نام کاربری خود را وارد کنید')
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': _('رمز عبور را وارد کنید'),
                'autocomplete': 'new-password'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': _('تکرار رمز عبور'),
                'autocomplete': 'new-password'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('ایمیل خود را وارد کنید')
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('نام')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('نام خانوادگی')
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('۰۹۱۲۳۴۵۶۷۸۹'),
                'type': 'tel'
            }),
            'national_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('کد ملی (۱۰ رقم)'),
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
                'placeholder': _('خیابان، پلاک، واحد'),
                'rows': 3
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('کد پستی ۱۰ رقمی'),
                'maxlength': '10'
            }),
            # switches
            'is_verified':    forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
            'is_staff':       forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
            'marketing_consent': forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
            'terms_accepted': forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
            'email_verified': forms.CheckboxInput(attrs={'class': 'form-check-input','role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop custom kwargs so base __init__ won’t error
        self.current_user = kwargs.pop('current_user', None)
        self.university   = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        # Help-text for username
        self.fields['username'].help_text = _('الزامی. ۱۵۰ نویسه یا کمتر. فقط حروف، اعداد و @/./+/-/_')

        # Password optional on edit
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = _('رمز جدید (در صورت تمایل)')
            self.fields['password2'].help_text = _('تکرار رمز جدید')

        # City dropdown: filter by POSTed province or existing one
        if 'province' in self.data:
            try:
                prov_id = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=prov_id)
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk and self.instance.province_id:
            self.fields['city'].queryset = City.objects.filter(province_id=self.instance.province_id)

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('این نام کاربری قبلاً ثبت شده است'))
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('این ایمیل قبلاً ثبت شده است'))
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            qs = User.objects.filter(mobile=mobile)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('این شماره موبایل قبلاً ثبت شده است'))
        return mobile

    def clean_national_code(self):
        code = self.cleaned_data.get('national_code')
        if code:
            qs = User.objects.filter(national_code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('این کد ملی قبلاً ثبت شده است'))
        return code

    def clean_birthday(self):
        bd = self.cleaned_data.get('birthday')
        if bd and bd > timezone.now().date():
            raise forms.ValidationError(_('تاریخ تولد نمی‌تواند در آینده باشد'))
        return bd

    def clean_password2(self):
        # On edit, if both blank → skip password validation
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        # On update: if both blank, skip validation (i.e. no password change)
        if self.instance and self.instance.pk and not password1 and not password2:
            return password2

        # Otherwise, call the parent class’s password2 validator
        return super(CustomUserCreationForm, self).clean_password2()

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)

            # Update password only if provided
            if self.cleaned_data.get('password1'):
                user.set_password(self.cleaned_data['password1'])

            if commit:
                user.save()
                self.save_m2m()

            # New user: create membership + log
            if not self.instance.pk:
                Membership.objects.create(
                    user=user,
                    university=self.university,
                    role='student',
                    is_confirmed=True
                )
                AdminActionLog.objects.create(
                    actor=self.current_user,
                    action='create_user',
                    target_user=user,
                    metadata={
                        'email': user.email,
                        'created_at': timezone.now().isoformat()
                    }
                )
            else:
                # Existing user: log update
                AdminActionLog.objects.create(
                    actor=self.current_user,
                    action='update_user',
                    target_user=user,
                    metadata={'updated_at': timezone.now().isoformat()}
                )

        return user
