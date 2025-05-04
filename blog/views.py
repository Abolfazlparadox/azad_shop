# blog/views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
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
        # increment view count
        BlogPost.objects.filter(pk=obj.pk).update(views=obj.views + 1)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object
        # Breadcrumb
        ctx['breadcrumb'] = [
            {'name': _('بلاگ'), 'url': reverse_lazy('posts')},
            {'name': post.title, 'url': ''},
        ]
        # comments

        ct = ContentType.objects.get_for_model(post)
        comments = (Comment.objects
                    .filter(content_type=ct, object_id=post.pk, parent__isnull=True, is_approved=True)
                    .select_related('user')
                    .prefetch_related('replies__user'))
        ctx['comments'] = comments

        # only provide the form if logged in
        if self.request.user.is_authenticated:
            ctx['comment_form'] = CommentForm()
        ctx['breadcrumb_title'] = post.title
        return ctx


