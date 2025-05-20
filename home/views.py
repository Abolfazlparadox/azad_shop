from django.views.generic import TemplateView
from django.http import JsonResponse
from iranian_cities.models import Province
from blog.models import BlogPost
from comment.models import Comment
from product.models import ProductCategory

class HomeTemplateView(TemplateView):
    template_name = 'home/index.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        last_blog_post  = BlogPost.objects.filter(is_published=True).order_by('-published_at')[0:5]
        last_comment = Comment.objects.filter(is_approved=True , content_type=18).order_by('-created_at').first()
        list_category = ProductCategory.objects.filter()
        ctx['last_blog_post'] = last_blog_post
        ctx['last_comment'] = last_comment
        ctx['list_category'] = list_category
        return ctx
#hi
def search_location(request):
    q = request.GET.get('q', '').strip()
    if q:
        qs = Province.objects.filter(name__icontains=q)
    else:
        qs = Province.objects.all()
    data = [{'id': p.id, 'name': p.name} for p in qs[:50]]
    return JsonResponse(data, safe=False)

from django.shortcuts import render

def custom_permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)





