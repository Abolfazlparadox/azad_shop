from django import forms
from .models import ContactMessage, Subject
from university.models import University
from django.utils.translation import gettext_lazy as _
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = [
            'first_name', 'last_name', 'email',
            'phone_number', 'subject', 'other_subject',
            'university','attachment', 'message'
        ]
        widgets = {
            'first_name':    forms.TextInput(attrs={'class':'form-control', 'placeholder':'نام'}),
            'last_name':     forms.TextInput(attrs={'class':'form-control', 'placeholder':'نام‌خانوادگی'}),
            'email':         forms.EmailInput(attrs={'class':'form-control', 'placeholder':'ایمیل'}),
            'phone_number':  forms.TextInput(attrs={'class':'form-control', 'placeholder':'شماره تماس'}),
            'subject':       forms.Select(attrs={'class':'form-select'}),
            'other_subject': forms.TextInput(attrs={'class':'form-control', 'placeholder':'اگر موضوع در لیست نیست'}),
            'message':       forms.Textarea(attrs={'class':'form-control', 'rows':4, 'placeholder':'متن پیام'}),
            'attachment':    forms.ClearableFileInput(attrs={'class':'form-control'}),
            'university':    forms.Select(attrs={'class':'form-select'}),
        }
        labels = {
            'first_name':   _('نام'),
            'last_name':    _('نام‌خانوادگی'),
            'email':        _('ایمیل'),
            'phone_number': _('تلفن'),
            'subject':      _('موضوع'),
            'other_subject': _('موضوع دیگر'),
            'message':      _('پیام شما'),
            'attachment':   _('ضمیمه (اختیاری)'),
            'university':   _('دانشگاه'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # اگر کاربر وارد شده، فیلدها را پر و readonly کن
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial  = user.last_name
            self.fields['email'].initial      = user.email
            self.fields['first_name'].widget.attrs['readonly'] = True
            self.fields['last_name'].widget.attrs['readonly']  = True
            self.fields['email'].widget.attrs['readonly']      = True
        # برای موضوع “سایت”، گزینه خالی دانشگاه
        self.fields['university'].queryset = University.objects.all()
        self.fields['subject'].queryset    = Subject.objects.all()
        self.fields['subject'].required    = False
        self.fields['other_subject'].required = False

    def clean(self):
        cleaned = super().clean()
        subject = cleaned.get('subject')
        other   = cleaned.get('other_subject')
        if not subject and not other:
            raise forms.ValidationError(_('لطفاً یک موضوع انتخاب یا وارد کنید.'))
        return cleaned
