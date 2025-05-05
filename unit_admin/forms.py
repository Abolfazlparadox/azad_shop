# unit_admin/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from account.models import User, Membership


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('CUSTOMER', 'مشتری'),
        ('ADMIN', 'ادمین'),
        ('STUDENT', 'دانشجو'),
        ('PROFESSOR', 'استاد'),
        ('EMPLOYEE', 'کارمند'),
        ('OFFI', 'دبیر رفاهی واحد'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="نقش کاربر",
        initial='CUSTOMER'
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'mobile', 'national_code', 'province', 'city',
            'address', 'postal_code', 'avatar', 'password1', 'password2'
        )

    def __init__(self, *args, **kwargs):
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        # تنظیم placeholderها
        self.fields['mobile'].widget.attrs['placeholder'] = '09123456789'
        self.fields['national_code'].widget.attrs['placeholder'] = '1234567890'

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Membership.objects.create(
                user=user,
                university=self.university,
                role=self.cleaned_data['role'],
                is_confirmed=True
            )
        return user