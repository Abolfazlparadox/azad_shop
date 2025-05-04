# blog/urls.py
from django.urls import path
    # wherever you defined it
from .views import BlogListView, BlogDetailView

urlpatterns = [
    path('posts/', BlogListView.as_view(), name='posts'),
    path('posts/<str:slug>/', BlogDetailView.as_view(), name='single_post'),
]