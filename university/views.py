# university/views.py

from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from account.models import Membership
from .models import University


class UniversityListView(ListView):
    model = University
    template_name = 'university/university_list.html'
    context_object_name = 'universities'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().filter(status=True).order_by('name')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def render_to_response(self, context, **response_kwargs):
        # اگر پارامتر ajax=1 ست باشد، فقط ردیف‌ها را برگردان
        if self.request.GET.get('ajax') == '1':
            return render(
                self.request,
                'university/includes/_university_rows.html',
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)


class UniversityDetailView(DetailView):
    model = University
    template_name = 'university/university_detail.html'
    context_object_name = 'university'

    def get_object(self, queryset=None):
        return get_object_or_404(
            University,
            slug=self.kwargs.get('slug'),
            status=True
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        uni = self.object

        # واکشی مدیر (نقش OFFI) تأییدشده برای این دانشگاه
        manager_membership = (
            Membership.objects
            .filter(university=uni, role=Membership.Role.UNIT_OFFICER, is_confirmed=True)
            .select_related('user')
            .first()
        )

        if manager_membership:
            ctx['manager_name'] = manager_membership.user.get_full_name() or manager_membership.user.username
            ctx['manager_user_id'] = manager_membership.user.id
        else:
            ctx['manager_name'] = _('هنوز تعیین نشده')
            ctx['manager_user_id'] = None

        # Breadcrumb
        ctx['breadcrumb'] = [
            {'name': _('دانشگاه‌ها'), 'url': reverse_lazy('university:list')},
            {'name': uni.name, 'url': ''},
        ]
        ctx['breadcrumb_title'] = uni.name
        return ctx