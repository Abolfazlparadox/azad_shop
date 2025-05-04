# comment/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _

from .forms import CommentForm
from .models import Comment
from blog.models import BlogPost


class CommentCreateView(LoginRequiredMixin, FormView):
    """
    Handles creation of comments and replies on blog posts.
    """
    login_url = 'login'
    form_class = CommentForm

    def form_valid(self, form):
        post_pk = self.kwargs['pk']
        post = get_object_or_404(BlogPost, pk=post_pk, is_published=True)
        comment = form.save(commit=False)
        comment.user = self.request.user

        # Generic relation to BlogPost
        ct = ContentType.objects.get_for_model(BlogPost)
        comment.content_type = ct
        comment.object_id = post_pk

        # Handle replies
        parent_id = self.request.POST.get('parent')
        if parent_id:
            try:
                parent = Comment.objects.get(
                    pk=parent_id,
                    content_type=ct,
                    object_id=post_pk
                )
                comment.parent = parent
            except Comment.DoesNotExist:
                pass  # ignore invalid parent

        comment.save()

        # Assign view permission to author on their own comment
        from guardian.shortcuts import assign_perm
        assign_perm('view_comment', self.request.user, comment)

        messages.success(
            self.request,
            _("دیدگاه شما با موفقیت ثبت شد و پس از تأیید نمایش داده می‌شود.")
        )
        return redirect('single_post', slug=post.slug)
