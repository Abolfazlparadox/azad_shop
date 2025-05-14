# unit_admin/context_processors.py
from account.models import Membership  # مدل درخواست رول
from contact.models import ContactMessage

def unit_admin_notifications(request):
    user = request.user
    if not user.is_authenticated:
        return {}

    # فرض: مدل MembershipRequest دارد درخواست‌های رول را نگه می‌دارد
    pending_roles = Membership.objects.filter(
        university=user.memberships.get(role='OFFI', is_confirmed=True).university,
        is_confirmed=False
    ).count()

    pending_tickets = ContactMessage.objects.filter(
        university=user.memberships.get(role='OFFI', is_confirmed=True).university,
        status='pending'
    ).count()

    return {
        'pending_roles_count': pending_roles,
        'pending_tickets_count': pending_tickets,
    }
