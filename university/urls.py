# university/urls.py

from django.urls import path
from .views import UniversityListView, UniversityDetailView

app_name = 'university'

urlpatterns = [
    path(
        '',
        UniversityListView.as_view(),
        name='list'
    ),
    path(
        '<slug:slug>/',
        UniversityDetailView.as_view(),
        name='detail'
    ),
]
