# unit_admin/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from account.models import User, Membership

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Membership.Role.choices,
        label="نقش کاربر",
        initial=Membership.Role.CUSTOMER
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'mobile', 'national_code', 'province', 'city',
            'address', 'postal_code', 'password1', 'password2'
        )
        labels = {
            'mobile': 'شماره موبایل (09xxxxxxxxx)',
            'national_code': 'کد ملی (۱۰ رقمی)',
        }

    def __init__(self, *args, **kwargs):
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

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