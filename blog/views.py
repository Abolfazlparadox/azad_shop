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
            slug=self.kwargs.get('slug'),
            is_published=True,
            published_at__lte=timezone.now()
        )
        # Increment view count atomically
        BlogPost.objects.filter(pk=obj.pk).update(views=obj.views + 1)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object
        user = self.request.user

        # Breadcrumbs
        ctx['breadcrumb'] = [
            {'name': _('بلاگ'), 'url': reverse_lazy('posts')},
            {'name': post.title,  'url': ''},
        ]
        ctx['breadcrumb_title'] = post.title

        # Fetch top‑level approved comments
        # fetch top‑level approved comments
        ct = ContentType.objects.get_for_model(post)
        comments = list(Comment.objects.filter(
            content_type=ct, object_id=post.pk,
            parent__isnull=True, is_approved=True
        ).select_related('user'))

        # determine which comments the current user may reply to
        for comment in comments:
            # only top‑level (they all are) and user logged in
            can_reply = False
            if user.is_authenticated:
                if user.is_superuser:
                    can_reply = True
                else:
                    # check OFFI membership against this post’s university
                    # assuming BlogPost has a .university FK
                    uni = getattr(post, 'university', None)
                    if uni:
                        is_offi = Membership.objects.filter(
                            user=user,
                            university=uni,
                            role=Membership.Role.UNIT_OFFICER,
                            is_confirmed=True
                        ).exists()
                        if is_offi:
                            can_reply = True
            comment.can_reply = can_reply

        ctx['comments'] = comments

        # === Add these two lines ===
        ctx['comment_app_label']  = post._meta.app_label   # e.g. 'blog'
        ctx['comment_model_name'] = post._meta.model_name  # e.g. 'blogpost'

        return ctx

