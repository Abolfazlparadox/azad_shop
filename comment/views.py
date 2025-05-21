# comment/views.py

from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts       import redirect, get_object_or_404
from django.views.generic   import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http            import Http404

from .forms     import CommentForm
from .models    import Comment
from account.models import Membership
from university.models import University  # import your University model

class CommentCreateGenericView(LoginRequiredMixin, FormView):
    form_class = CommentForm
    login_url  = 'login'

    def dispatch(self, request, *args, **kwargs):
        # Load content type & target object
        app_label  = kwargs['app_label']
        model_name = kwargs['model_name']
        obj_id     = kwargs['object_id']

        ct = get_object_or_404(ContentType, app_label=app_label, model=model_name)
        self.content_type = ct
        self.object_id    = obj_id
        self.target       = ct.get_object_for_this_type(pk=obj_id)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        parent_id = form.cleaned_data.get('parent')  # now controlled by the form

        if parent_id:
            parent = get_object_or_404(
                Comment,
                pk=parent_id,
                content_type=self.content_type,
                object_id=self.object_id
            )
            form.instance.is_approved = True
            if parent.parent is not None:
                raise Http404("امکان پاسخ‌گویی به پاسخ وجود ندارد.")


            user = self.request.user

            # 2) allow superusers always
            if not user.is_superuser:
                # determine the university of the target
                if isinstance(self.target, University):
                    target_university = self.target
                elif hasattr(self.target, 'university'):
                    target_university = getattr(self.target, 'university')
                else:
                    # target has no university: disallow replies
                    raise Http404("امکان پاسخ‌گویی وجود ندارد.")

                # 3) check OFFI membership for that university
                is_offi = Membership.objects.filter(
                    user=user,
                    university=target_university,
                    role=Membership.Role.UNIT_OFFICER,
                    is_confirmed=True
                ).exists()

                if not is_offi:
                    raise Http404("شما دسترسی لازم برای پاسخ‌گویی ندارید.")

            # passed all checks, attach parent
            form.instance.parent = parent

        # save the comment
        form.instance.user         = self.request.user
        form.instance.content_type = self.content_type
        form.instance.object_id    = self.object_id
        form.save()

        messages.success(
            self.request,
            _("دیدگاه با موفقیت ثبت شد و پس از تأیید نمایش داده می‌شود.")
        )

        # redirect back to the object’s page
        # require each model to implement get_absolute_url()
        try:
            return redirect(self.target.get_absolute_url())
        except AttributeError:
            # fallback to HTTP_REFERER
            return redirect(self.request.META.get('HTTP_REFERER', '/'))
