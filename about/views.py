from django.views.generic import TemplateView
from home.models import SiteSetting
from comment.models import Comment
from account.models import Membership

class AboutView(TemplateView):
    template_name = 'about-us.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # 1) تنظیمات اصلی سایت
        setting = SiteSetting.objects.get(is_main_setting=True)
        ctx['site_setting'] = setting

        offi_memberships = Membership.objects.filter(
            role='OFFI', is_confirmed=True
        ).select_related('user', 'university')
        ctx['team'] = [
            {
                'user': m.user,
                'role_display': m.get_role_display(),
                'university_name': m.university.name
            }
            for m in offi_memberships
        ]
        comments = Comment.objects.filter(
            content_type=18,
            object_id=setting.pk,
            is_approved=True
        ).select_related('user')
        ctx['comments'] = comments

        return ctx
