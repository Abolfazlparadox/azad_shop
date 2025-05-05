# unit_admin/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from iranian_cities.models import Province, City
from account.models import User, Membership



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
            'username', 'password1', 'password2', 'first_name', 'last_name',
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



    def save(self, commit=True):
        user = super().save(commit=commit)
        # Add any additional save logic here
        return user