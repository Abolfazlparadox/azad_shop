# university/views.py

from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from account.models import Membership
from blog.models import BlogPost
from comment.forms import CommentForm
from comment.models import Comment
from product.models import ProductCategory
from .models import University


class UniversityListView(ListView):
    model = University
    template_name = 'university/university_list.html'
    context_object_name = 'universities'
    paginate_by = 10
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        last_blog_post  = BlogPost.objects.filter(is_published=True).order_by('-published_at')[0:5]
        list_category = ProductCategory.objects.filter(parent=None).order_by('title')[0:5]
        ctx['last_blog_post'] = last_blog_post
        ctx['list_category'] = list_category
        return ctx
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
        uni  = self.object
        user = self.request.user

        # OFFI‑admin lookup
        manager = (Membership.objects
                   .filter(university=uni,
                           role=Membership.Role.UNIT_OFFICER,
                           is_confirmed=True)
                   .select_related('user')
                   .first())
        if manager:
            ctx['manager_name']    = manager.user.get_full_name() or manager.user.username
            ctx['manager_user_id'] = manager.user.id
        else:
            ctx['manager_name']    = _('هنوز تعیین نشده')
            ctx['manager_user_id'] = None

        # Breadcrumbs
        ctx['breadcrumb']       = [
            {'name': _('دانشگاه‌ها'), 'url': reverse_lazy('university:list')},
            {'name': uni.name,          'url': ''},
        ]
        ctx['breadcrumb_title'] = uni.name

        # Comments: top‑level, approved
        ct = ContentType.objects.get_for_model(uni)
        comments = list(Comment.objects.filter(
            content_type=ct,
            object_id=uni.pk,
            parent__isnull=True,
            is_approved=True
        ).select_related('user'))

        # Annotate can_reply
        for comment in comments:
            comment.can_reply = False
            if user.is_authenticated:
                if user.is_superuser:
                    comment.can_reply = True
                else:
                    # only OFFI‑admins of *this* university
                    comment.can_reply = Membership.objects.filter(
                        user=user,
                        university=uni,
                        role=Membership.Role.UNIT_OFFICER,
                        is_confirmed=True
                    ).exists()

        ctx['comments']             = comments
        if user.is_authenticated:
            ctx['comment_form']      = CommentForm()
        ctx['comment_app_label']     = 'university'
        ctx['comment_model_name']    = 'university'
        return ctx