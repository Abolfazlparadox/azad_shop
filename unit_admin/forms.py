# unit_admin/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.utils import timezone
from iranian_cities.models import Province, City
from slugify import slugify
from django.contrib.auth.password_validation import validate_password
from account.models import User, Membership, AdminActionLog, Address
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from contact.models import ContactMessage
from django.forms import ModelForm
from product.models import ProductAttributeType, ProductAttribute, Discount, Product, ProductDescription, \
    ProductVariant, ProductCategory

User = get_user_model()


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['attributes', 'stock', 'price_override', 'discount']
        widgets = {
            'attributes': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'discount':   forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'attributes':    _('ویژگی‌ها'),
            'stock':         _('موجودی'),
            'price_override': _('قیمت ویژه'),
            'discount':      _('تخفیف'),
        }
        error_messages = {
            'attributes': {
                'required': _('لطفاً حداقل یک ویژگی انتخاب کنید.'),
            },
            'stock': {
                'required': _('وارد کردن موجودی الزامی است.'),
                'invalid':  _('موجودی باید عددی صحیح باشد.'),
            },
            'price_override': {
                'invalid': _('قیمت ویژه باید عددی صحیح باشد.'),
            },
        }
class ProductDescriptionForm(forms.ModelForm):
    class Meta:
        model = ProductDescription
        fields = ['Image', 'title_description', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'Image':             _('تصویر توضیح'),
            'title_description': _('تیتر توضیح'),
            'description':       _('متن توضیح'),
        }
        error_messages = {
            'title_description': {
                'max_length': _('تیتر توضیح نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.'),
            },
            'description': {
                'required': _('متن توضیح را وارد کنید.'),
            },
        }
ProductVariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    form=ProductVariantForm,
    extra=1,
    can_delete=True
)

ProductDescriptionFormSet = inlineformset_factory(
    Product, ProductDescription,
    form=ProductDescriptionForm,
    extra=1,
    can_delete=True
)
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
            'is_deleted',
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
            'is_deleted': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        # تعیین required بودن
        for fname in ('username', 'email', 'password1', 'password2'):
            self.fields[fname].required = True
            self.fields[fname].help_text = _('این فیلد الزامی است')

        # سایر فیلدها را اختیاری کنید
        optional = set(self.fields) - {'username', 'email', 'password1', 'password2'}
        for fname in optional:
            self.fields[fname].required = False
            # حذف HTML5 required از ویجت
            self.fields[fname].widget.attrs.pop('required', None)

        # در ویرایش: مقدار اولیه بدهید
        if self.instance and self.instance.pk:
            for field in self.fields:
                if hasattr(self.instance, field):
                    self.fields[field].initial = getattr(self.instance, field)
            # رمز را اختیاری کنید
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = _('رمز جدید (اختیاری)')
            self.fields['password2'].help_text = _('تکرار رمز جدید')

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
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        # On update: if both blank, skip password change
        if self.instance.pk and not password1 and not password2:
            return password2

        # Both must be provided
        if not password1 or not password2:
            raise forms.ValidationError(_('لطفاً هر دو فیلد رمز را پر کنید'))

        # Must match
        if password1 != password2:
            raise forms.ValidationError(_('رمز عبور و تکرار آن یکسان نیستند'))

        # Run Django's built-in validators (length, complexity, etc.)
        try:
            validate_password(password2, user=self.instance)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        # اگر رمز وارد شده باشد، ستش کنید
        new_pwd = self.cleaned_data.get('password1')
        if new_pwd:
            user.set_password(new_pwd)
        if commit:
            user.save()
            self.save_m2m()
            # در ایجاد: عضویت بسازید
            if not self.instance.pk:
                Membership.objects.create(
                    user=user,
                    university=self.university,
                    role='student', is_confirmed=True
                )
        return user

class AddressForm(forms.ModelForm):
    # 1) Declare the 'user' field here, not inside Meta
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=_('کاربر'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Address
        fields = [
            'name', 'user', 'category', 'address',
            'postal_code', 'telephone',
            'province', 'city', 'active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.Select(attrs={
                'class': 'form-select',
                'data-province-select': True
            }),
            'city':    forms.Select(attrs={
                'class': 'form-select',
                'data-city-select': True
            }),
            'active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('عنوان نشانی'),
            'category': _('دسته‌بندی'),
            'address': _('آدرس کامل'),
            'postal_code': _('کد پستی'),
            'telephone': _('تلفن'),
            'province': _('استان'),
            'city': _('شهر'),
            'active': _('نشانی پیش‌فرض'),
        }

    def __init__(self, *args, **kwargs):
        # Pop the passed-in university
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)

        # 1) Filter users to those confirmed in this university
        if self.university:
            qs = User.objects.filter(
                memberships__university=self.university,
                memberships__is_confirmed=True
            ).distinct()
        else:
            qs = User.objects.none()
        self.fields['user'].queryset = qs

        # 2) Province dropdown always all provinces
        self.fields['province'].queryset = Province.objects.all()

        # 3) City dropdown: if POST, filter by chosen province
        if 'province' in self.data:
            try:
                pid = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=pid)
            except (ValueError, TypeError):
                self.fields['city'].queryset = City.objects.none()
        # on update: existing instance has province → populate cities
        elif self.instance and self.instance.pk and self.instance.province_id:
            # directly filter City by province_id
            self.fields['city'].queryset = City.objects.filter(
            province_id=self.instance.province_id)
        else:
            self.fields['city'].queryset = City.objects.none()

    def clean_user(self):
        user = self.cleaned_data['user']
        # ensure the user actually belongs to this university
        if not user.memberships.filter(
            university=self.university,
            is_confirmed=True
        ).exists():
            raise forms.ValidationError(_('این کاربر به دانشگاه شما تعلق ندارد.'))
        return user

    def save(self, commit=True):
        addr = super().save(commit=False)
        if commit:
            addr.save()
            # if this address is set to active, deactivate all others
            if addr.active:
                Address.objects.filter(
                    user=addr.user
                ).exclude(pk=addr.pk).update(active=False)
        return addr

class ProductAttributeTypeForm(ModelForm):
    class Meta:
        model = ProductAttributeType
        fields = ['name']

class ProductAttributeForm(ModelForm):
    class Meta:
        model = ProductAttribute
        fields = ['type', 'value', 'color', 'image']

class DiscountForm(ModelForm):
    class Meta:
        model = Discount
        fields = ['code','description','discount_type','amount','max_discount',
                  'valid_from','valid_to','max_usage','products','categories']
        widgets = {
            'products': forms.SelectMultiple(attrs={'class':'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class':'form-select'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = [
            'slug', 'sku', 'university',
            'created_at', 'updated_at', 'old_price'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class':'form-control',
                'placeholder': _('عنوان محصول را وارد کنید')
            }),
            'categories': forms.SelectMultiple(attrs={'class':'form-select'}),
            'main_image': forms.ClearableFileInput(attrs={
                'class':'form-control','accept':'image/*'
            }),
            'brand': forms.Select(attrs={'class':'form-select'}),
            'weight': forms.NumberInput(attrs={
                'class':'form-control','step':'0.01','min':0
            }),
            'dimensions': forms.TextInput(attrs={
                'class':'form-control',
                'placeholder': _('طول×عرض×ارتفاع (سانتی‌متر)')
            }),
            'short_description':forms.Textarea(attrs={
                'class':'form-control',
                'placeholder': _('توضیحات کوتاه')}),
            'tags': forms.SelectMultiple(attrs={'class':'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'is_deleted': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
        labels = {
            'title': _('عنوان'),
            'categories': _('دسته‌بندی‌ها'),
            'main_image': _('تصویر اصلی'),
            'brand': _('برند'),
            'weight': _('وزن (کیلوگرم)'),
            'dimensions': _('ابعاد'),
            'short_description':_('توضیحات کوتاه'),
            'tags': _('تگ‌ها'),
            'is_active': _('فعال/غیرفعال'),
            'is_deleted': _('حذف نرم'),
        }
        help_texts = {
            'is_active': _('با برداشتن تیک، محصول از فروشگاه پنهان می‌شود.'),
            'is_deleted': _('با تیک‌زدن، محصول به صورت نرم حذف می‌شود.'),
            'weight': _('وزن را بر حسب کیلوگرم وارد کنید.'),
            'dimensions': _('ابعاد را به صورت طول×عرض×ارتفاع وارد کنید.'),
        }
        error_messages = {
            'title': {
                'required': _('وارد کردن عنوان محصول الزامی است.'),
                'max_length': _('عنوان نباید بیش از ۳۰۰ کاراکتر باشد.'),
            },
            'categories': {
                'required': _('لطفاً حداقل یک دسته‌بندی انتخاب نمایید.'),
            },
            'main_image': {
                'required': _('بارگذاری تصویر اصلی محصول الزامی است.'),
                'invalid': _('لطفاً یک فایل تصویر معتبر انتخاب کنید.'),
            },
            'brand': {
                'invalid_choice': _('برند انتخاب شده معتبر نیست.'),
            },
            'weight': {
                'invalid': _('وزن باید عددی صحیح یا اعشاری باشد.'),
            },
            'dimensions': {
                'max_length': _('طول توضیحات بیش از حد مجاز است.'),
            },
            'short_description':{
                'required': _('این فیلد نیاز است ')
            }
        }

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is None:
            return weight
        if weight < 0:
            raise forms.ValidationError(
                _('وزن نمی‌تواند منفی باشد.'),
                code='invalid_weight'
            )
        return weight

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None:
            return stock
        if stock < 0:
            raise forms.ValidationError(
                _('موجودی نمی‌تواند منفی باشد.'),
                code='invalid_stock'
            )
        return stock

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        # حذف slug از فیلدهای قابل ویرایش
        fields = [
            'title', 'parent', 'icon',
            'is_active', 'is_deleted'
        ]
        widgets = {
            'title':      forms.TextInput(attrs={'class':'form-control'}),
            'parent':     forms.Select(attrs={'class':'form-select'}),
            'icon':       forms.ClearableFileInput(attrs={'class':'form-control','accept':'.svg,.png'}),
            'is_active':  forms.CheckboxInput(attrs={'class':'form-check-input','role':'switch'}),
            'is_deleted': forms.CheckboxInput(attrs={'class':'form-check-input','role':'switch'}),
        }
        labels = {
            'title':      _('عنوان'),
            'parent':     _('دسته والد'),
            'icon':       _('آیکون (SVG/PNG)'),
            'is_active':  _('فعال'),
            'is_deleted': _('حذف نرم'),
        }
        help_texts = {
            'title': _('نماد یگانگی: دو دسته با همین عنوان در یک دانشگاه مجاز نیست.'),
        }

    def __init__(self, *args, **kwargs):
        # دریافت یونیورسیتی از ویو
        self.university = kwargs.pop('university', None)
        super().__init__(*args, **kwargs)
        # فقط والد‌های همان دانشگاه
        if self.university:
            self.fields['parent'].queryset = ProductCategory.objects.filter(
                university=self.university,
                is_deleted=False
            )

    def clean_title(self):
        title = self.cleaned_data['title']
        qs = ProductCategory.objects.filter(
            title=title,
            university=self.university
        )
        # اگر در ویرایش، رکورد خودش را کنار بگذارد
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('یک دسته با این عنوان در دانشگاه شما قبلاً ثبت شده است.'))
        return title

    def save(self, commit=True):
        # قبل از ذخیره، slug و university را تنظیم می‌کنیم
        instance = super().save(commit=False)
        if not instance.slug or instance.title != self.instance.title:
            instance.slug = slugify(instance.title, allow_unicode=True)
        if self.university:
            instance.university = self.university
        if commit:
            instance.save()
            # برای M2M ندارد
        return instance

class AdminSettingsForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_('رمز عبور جدید'),
        widget=forms.PasswordInput(attrs={'class':'form-control'}),
        required=False
    )
    password2 = forms.CharField(
        label=_('تکرار رمز عبور'),
        widget=forms.PasswordInput(attrs={'class':'form-control'}),
        required=False
    )

    class Meta:
        model = User
        fields = (
            'username','email','first_name','last_name',
            'mobile','national_code','birthday','avatar',
            'province','city','address','postal_code',
            'password1',
            'password2',
            # فیلدهای فقط خواندنی:
            'is_verified', 'is_staff', 'is_active',
            'marketing_consent', 'terms_accepted',
            'email_verified', 'is_deleted',
        )
        widgets = {
            k: forms.TextInput(attrs={'class':'form-control'})
            for k in ['username','email','first_name','last_name',
                      'mobile','national_code','address','postal_code']
        }
        widgets.update({
            'birthday': forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'avatar': forms.ClearableFileInput(attrs={'class':'form-control','accept':'image/*'}),
            'province': forms.Select(attrs={'class':'form-select','data-province-select':True}),
            'city': forms.Select(attrs={'class':'form-select','data-city-select':True}),

        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        readonly_fields = [
            'is_verified', 'is_staff', 'is_active',
            'marketing_consent', 'terms_accepted',
            'email_verified', 'is_deleted'
        ]
        for f in readonly_fields:
            if f in self.fields:
                self.fields[f].disabled = True
                # اختیاری: اضافه کردن کلاس CSS برای نشان دادن حالت غیرفعال
                self.fields[f].widget.attrs.update({'class': 'form-check-input m-2'})
        # شهر-استان
        self.fields['province'].queryset = Province.objects.all()
        if 'province' in self.data:
            try:
                pid = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=pid)
            except:
                self.fields['city'].queryset = City.objects.none()
        elif self.instance.province_id:
            self.fields['city'].queryset = City.objects.filter(province_id=self.instance.province_id)
        else:
            self.fields['city'].queryset = City.objects.none()

        # help texts
        for f in ['username','email']:
            self.fields[f].help_text = _('این فیلد الزامی است')

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', _('رمزها مطابقت ندارند'))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get('password1')
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
        return user


class ContactAnswerForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['answer']
        widgets = {
            'answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': _('متن پاسخ خود را اینجا بنویسید...')
            }),
        }
        labels = {
            'answer': _('متن پاسخ'),
        }
        help_texts = {
            'answer': _('پس از ارسال، وضعیت پیام به «پاسخ‌داده‌شده» تغییر می‌کند و تاریخ پاسخ ثبت می‌شود.'),
        }

    def clean_answer(self):
        ans = self.cleaned_data.get('answer', '').strip()
        if not ans:
            raise forms.ValidationError(_('متن پاسخ نمی‌تواند خالی باشد.'))
        return ans