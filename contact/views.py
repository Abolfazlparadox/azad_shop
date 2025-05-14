from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView
from django.contrib import messages
from django.core.mail import mail_admins
from django.utils.translation import gettext_lazy as _
from home.models import SiteSetting
from .models import ContactMessage
from .forms import ContactForm

class ContactCreateView(CreateView):
    model = ContactMessage
    form_class = ContactForm
    template_name = 'contact/contact-us.html'
    success_url = reverse_lazy('contact:contact')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # تنها تنظیمات اصلی
        ctx['site'] = SiteSetting.objects.filter(is_main_setting=True).first()
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['user'] = self.request.user
        return kw

    def form_valid(self, form):
        resp = super().form_valid(form)
        # اعلان ایمیلی:
        subject = f"پیام جدید تماس از {self.object.first_name} {self.object.last_name}"
        message = (
            f"موضوع: {self.object.subject or self.object.other_subject}\n"
            f"دانشگاه: {self.object.university or 'سایت'}\n"
            f"ایمیل: {self.object.email}\n\n"
            f"{self.object.message}"
        )
        mail_admins(subject, message, fail_silently=True)
        messages.success(self.request, _('پیام شما با موفقیت ارسال شد.'))
        return resp

class ContactListView(ListView):
    model = ContactMessage
    template_name = 'contact/contact-us.html'
    context_object_name = 'messages'
    paginate_by = 20

    def get_queryset(self):
        # ادمین‌های دانشگاه فقط پیام‌های دانشگاه خود؛ سوپریوزر همه را می‌بینند
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        offi = self.request.user.memberships.filter(role='OFFI', is_confirmed=True).first()
        if offi:
            return qs.filter(university=offi.university)
        return qs.none()
