from django.urls import path

from home.views import HomeTemplateView
from .views import search_location

urlpatterns = [
    path('', HomeTemplateView.as_view(), name='home'),
    path('search-location/', search_location, name='search_location'),
]