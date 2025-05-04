from django.views.generic import TemplateView
from django.http import JsonResponse
from iranian_cities.models import Province

class HomeTemplateView(TemplateView):
    template_name = 'home/index.html'


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