import random
from datetime import timedelta
from django.db import transaction
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
import uuid
from django.core.exceptions import ValidationError
from django.contrib.auth.models import UserManager
from iranian_cities.models import Province, City
from django.conf import settings
from university.models import University

def validate_national_code(value):
    # Basic checks
    if len(value) != 10 or not value.isdigit():
        raise ValidationError(_('کد ملی باید 10 رقم باشد'))

    # Check for invalid sequences
    if value in ['0000000000', '1111111111', '2222222222', '3333333333',
                 '4444444444', '5555555555', '6666666666', '7777777777',
                 '8888888888', '9999999999']:
        raise ValidationError(_('کد ملی نامعتبر است'))

    # Checksum calculation
    check = int(value[9])
    s = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
    valid = (s < 2 and check == s) or (s >= 2 and check == (11 - s))

    if not valid:
        raise ValidationError(_('کد ملی نامعتبر است'))

class CustomUserQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

class CustomUserManager(UserManager.from_queryset(CustomUserQuerySet)):
    """Single manager: .alive() & .deleted() available."""
    pass

class User(AbstractUser):
    require_2fa = models.BooleanField(_('نیاز به احراز دو مرحله‌ای'), default=False)
    # Authentication Fields
    username = models.CharField(_('نام کاربری'),max_length=150,unique=True,help_text=_('الزامی. 150 حرف یا کمتر. فقط حروف، اعداد و @/./+/-/_'),validators=[AbstractUser.username_validator],error_messages={'unique': _("این نام کاربری قبلا ثبت شده است."),})
    email = models.EmailField(_('آدرس ایمیل'),unique=True,error_messages={'unique': _("این ایمیل قبلا ثبت شده است.")})
    # Security Fields
    last_login_ip = models.GenericIPAddressField(_('آخرین آی پی ورود'), null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    otp_secret = models.CharField(_('کلید OTP'), max_length=32, blank=True)

    is_verified = models.BooleanField(_('تایید شده'),default=False,help_text=_('آیا حساب کاربری توسط مدیریت تایید شده است؟'))
    is_staff = models.BooleanField(_('وضعیت کارکنان'),default=False,help_text=_('مشخص می کند که آیا کاربر می تواند به این سایت مدیریت وارد شود یا خیر.'),)
    is_active = models.BooleanField(_('فعال'),default=True,help_text=_('مشخص می کند که آیا این کاربر باید به عنوان فعال در نظر گرفته شود.'),)
    # Personal Information
    first_name = models.CharField(_('نام'), max_length=150, blank=True)
    last_name = models.CharField(_('نام خانوادگی'), max_length=150, blank=True)
    mobile = PhoneNumberField(_('شماره موبایل'),region='IR',unique=True,null=True,blank=True,error_messages={'unique': _("این شماره موبایل قبلا ثبت شده است.")})
    national_code = models.CharField(_('کد ملی'),max_length=10,unique=True,null=True,blank=True,validators=[validate_national_code])
    birthday = models.DateField(_('تاریخ تولد'), null=True, blank=True)
    avatar = models.ImageField(_('تصویر پروفایل'),upload_to='profiles/%Y/%m/',null=True,blank=True,help_text=_('تصویر مربعی با حداقل اندازه 200x200 پیکسل'))
    # Address Information
    province = models.ForeignKey(Province,on_delete=models.CASCADE,verbose_name=_('استان'),null=True,blank=True,)
    city = models.ForeignKey(City,on_delete=models.CASCADE,verbose_name=_('شهر'),null=True,blank=True,)
    address = models.TextField(_('آدرس دقیق'), blank=True)
    postal_code = models.CharField(_('کد پستی'), max_length=10, blank=True)
    # Add foreign key to University
    universities = models.ManyToManyField(University,through='Membership',related_name='users',verbose_name=_('دانشگاه‌ها'),blank=True)
    is_deleted = models.BooleanField(_('حذف شده'), default=False)
    deleted_at = models.DateTimeField(_('تاریخ حذف'), null=True, blank=True)
    # Consent Fields
    terms_accepted = models.BooleanField(_('پذیرش شرایط'), default=False)
    terms_accepted_at = models.DateTimeField(_('تاریخ پذیرش شرایط'), null=True, blank=True)
    marketing_consent = models.BooleanField(_('مجوز بازاریابی'), default=False)
    # Timestamps
    date_joined = models.DateTimeField(_('تاریخ ثبت نام'), default=timezone.now)
    updated_at = models.DateTimeField(_('آخرین بروزرسانی'), auto_now=True)
    objects = CustomUserManager()
    deleted_objects = UserManager()  # For accessing deleted users
    email_verified = models.BooleanField(
        _("ایمیل تأیید شده"),
        default=False,
        help_text=_("تعیین می‌کند که آیا کاربر ایمیل خود را تأیید کرده است")
    )
    email_verification_code = models.CharField(max_length=6, null=True, blank=True)
    email_verification_code_created = models.DateTimeField(null=True, blank=True)

    def generate_email_verification_code(self):
        """Generate 6-digit numeric code"""
        code = str(random.randint(100000, 999999))  # 6-digit number
        self.email_verification_code = code
        self.email_verification_code_created = timezone.now()
        self.save(update_fields=['email_verification_code', 'email_verification_code_created'])
        return code

    def is_verification_code_expired(self):
        """Check if code is expired (15 minutes)"""
        if not self.email_verification_code_created:
            return True
        expiration = self.email_verification_code_created + timezone.timedelta(minutes=15)
        return timezone.now() > expiration

    def clear_verification_code(self):
        self.email_verification_code = None
        self.email_verification_code_created = None
        self.save(update_fields=['email_verification_code', 'email_verification_code_created'])

    class Level(models.IntegerChoices):
        UNVERIFIED = 0, _('عدم تأیید ایمیل')
        EMAIL_CONFIRMED = 1, _('کاربر تأییدشده ایمیل')
        PROFILE_COMPLETED = 2, _('پروفایل تکمیل‌شده')
        MEMBERSHIP_CONFIRMED = 3, _('عضویت تأییدشده')

    @property
    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def check_lock_expiry(self):
        if self.locked_until and timezone.now() > self.locked_until:
            self.locked_until = None
            self.failed_login_attempts = 0
            self.save()
    @property
    def access_level(self) -> int:
        """
        Determine the user's current level:
        1️⃣ Email confirmed (level1)
        2️⃣ Profile complete (level2)
        3️⃣ Membership confirmed (level3)
        """
        # 1: Email verification
        if not self.email_verified:
            return self.Level.UNVERIFIED
        # 2: Profile fields check
        required_fields = [
            self.first_name,
            self.last_name,
            self.mobile,
            self.national_code,
            self.province,
            self.city
        ]
        if any(v in (None, "") for v in required_fields):
            return self.Level.EMAIL_CONFIRMED
        # 3: Confirmed membership
        if self.memberships.filter(is_confirmed=True).exists():
            return self.Level.MEMBERSHIP_CONFIRMED
        return self.Level.PROFILE_COMPLETED

    class Meta:
        verbose_name = _('کاربر')
        verbose_name_plural = _('کاربران')
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['email']),
            models.Index(fields=['national_code']),
            models.Index(fields=['is_deleted']),
        ]
        ordering = ['-date_joined']

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    @property
    def active_role_display(self):
        # get first confirmed membership
        m = self.memberships.filter(is_confirmed=True).first()
        if m:
            return m.get_role_display()
        # fallback label for default customer role
        return dict(Membership.Role.choices).get(Membership.Role.CUSTOMER, 'مشتری')
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    @property
    def age(self):
        if self.birthday:
            today = timezone.now().date()
            return today.year - self.birthday.year - (
                    (today.month, today.day) < (self.birthday.month, self.birthday.day)
            )
        return None

class Membership(models.Model):
    class Role(models.TextChoices):
        CUSTOMER  = 'customer', _('مشتری')
        ADMIN = 'admin',_('ادمین')
        STUDENT   = 'student',  _('دانشجو')
        PROFESSOR = 'professor',_('استاد')
        Employee = 'Employee',_('کارمند')
        UNIT_OFFICER = 'OFFI', _('دبیر رفاهی واحد')

        # add more roles here…

    user        = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name='memberships',
                                    verbose_name=_('کاربر'))
    university  = models.ForeignKey(University,
                                    on_delete=models.CASCADE,
                                    related_name='memberships',
                                    verbose_name=_('دانشگاه'),
                                    blank=True,
                                    )
    role        = models.CharField(max_length=20,
                                   choices=Role.choices,
                                   default=Role.CUSTOMER,
                                   verbose_name=_('نقش'))
    code        = models.CharField(max_length=64,
                                   verbose_name=_('کد نقش'))
    is_confirmed= models.BooleanField(default=False,
                                      verbose_name=_('تایید شده'))
    requested_at= models.DateTimeField(auto_now_add=True,
                                       verbose_name=_('درخواست در'))
    confirmed_at= models.DateTimeField(null=True, blank=True,
                                       verbose_name=_('تایید در'))

    class Meta:
        verbose_name = _('نقش')
        verbose_name_plural = _('نقش ‌ها')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role'],
                condition=models.Q(role='OFFI'),  # فقط برای نقش دبیر رفاهی
                name='unique_offi_per_user'
            )
        ]

    def confirm(self):
        """تایید عضویت و غیرفعال کردن سایر نقش‌ها"""
        with transaction.atomic():
            # غیرفعال کردن تمام نقش‌های کاربر در این دانشگاه
            Membership.objects.filter(
                user=self.user,
                university=self.university
            ).exclude(pk=self.pk).update(is_confirmed=False)

            # تایید نقش دبیر رفاهی
            self.is_confirmed = True
            self.confirmed_at = timezone.now()
            self.save()

    def __str__(self):
        return f"{self.user} as {self.get_role_display()} @ {self.university}"

class Address(models.Model):
    class Category(models.TextChoices):
        HOME  = 'home',  _('خانه')
        WORK  = 'work',  _('محل کار')
        OTHER = 'other', _('سایر')

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('کاربر')
    )
    name        = models.CharField(
        max_length=100,
        verbose_name=_('عنوان نشانی'),
        help_text=_('برای مثال: خانه، محل کار')
    )
    category    = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.HOME,
        verbose_name=_('دسته‌بندی'),
    )
    address     = models.TextField(
        verbose_name=_('آدرس کامل'),
        help_text=_('خیابان، پلاک، واحد و ...')
    )
    postal_code = models.CharField(
        max_length=10,
        verbose_name=_('کد پستی'),
        help_text=_('کد پستی 10 رقمی')
    )
    telephone   = models.CharField(
        max_length=20,
        verbose_name=_('تلفن'),
        help_text=_('شماره تماس برای این نشانی')
    )
    province    = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        verbose_name=_('استان')
    )
    city        = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        verbose_name=_('شهر')
    )
    active      = models.BooleanField(
        default=False,
        verbose_name=_('نشانی پیش‌فرض')
    )
    created_at  = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('ایجاد شده در')
    )
    updated_at  = models.DateTimeField(
        auto_now=True,
        verbose_name=_('بروزرسانی شده در')
    )

    class Meta:
        verbose_name = _('نشانی')
        verbose_name_plural = _('نشانی‌ها')
        ordering = ['-active', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'active']),
        ]
        unique_together = [('user', 'name')]  # یک نام نشانی نباید تکراری باشد

    def __str__(self):
        return f"{self.get_category_display()} — {self.name}"  # e.g. "خانه — نشانی اصلی"
