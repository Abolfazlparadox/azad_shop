from django.urls import path

from home.views import HomeTemplateView, custom_permission_denied_view
from .views import search_location

urlpatterns = [
    path('', HomeTemplateView.as_view(), name='home'),
    path('search-location/', search_location, name='search_location'),
    path('403',custom_permission_denied_view,name='403'),
]