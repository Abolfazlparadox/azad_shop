# blog/views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from account.models import Membership
from comment.forms import CommentForm
from comment.models import Comment
from university.models import University
from .models import BlogPost



class BlogListView(ListView):
    model = BlogPost
    template_name = 'blog/blog-list.html'
    context_object_name = 'posts'
    paginate_by = 6  # adjust as needed

    def get_queryset(self):
        # Only show published posts
        return (super().get_queryset()
                    .filter(is_published=True, published_at__lte=timezone.now())
                    .select_related('author', 'category')
                    .prefetch_related('tags'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Breadcrumb
        ctx['breadcrumb'] = [
            {'name': _('بلاگ'), 'url': reverse_lazy('posts')},
            {'name': _('لیست پست‌ها'), 'url': ''},
        ]
        ctx['breadcrumb_title'] = _('بلاگ : لیست پست‌ها')
        return ctx

class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/blog-detail.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        obj = get_object_or_404(
            BlogPost,
            slug=self.kwargs['slug'],
            is_published=True,
            published_at__lte=timezone.now()
        )
        BlogPost.objects.filter(pk=obj.pk).update(views=obj.views + 1)
        return obj

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        post = self.object
        user = self.request.user

        # fetch top‑level approved comments
        ct = ContentType.objects.get_for_model(post)
        comments = list(Comment.objects.filter(
            content_type=ct,
            object_id=post.pk,
            parent__isnull=True,
            is_approved=True
        ).select_related('user'))

        # determine can_reply per comment
        for comment in comments:
            # default: no reply
            comment.can_reply = False

            # only top‑level comments considered
            if user.is_authenticated:
                if user.is_superuser:
                    comment.can_reply = True
                else:
                    # find university of this blog post
                    uni = getattr(post, 'university', None)
                    if isinstance(uni, University):
                        is_offi = Membership.objects.filter(
                            user=user,
                            university=uni,
                            role=Membership.Role.UNIT_OFFICER,
                            is_confirmed=True
                        ).exists()
                        comment.can_reply = is_offi

        ctx['comments']     = comments
        if user.is_authenticated:
            ctx['comment_form'] = CommentForm()
        ctx['comment_app_label']  = post._meta.app_label
        ctx['comment_model_name'] = post._meta.model_name

        return ctx

