# blog/urls.py
from django.urls import path
    # wherever you defined it
from .views import  CommentCreateView

app_name = 'comment'

urlpatterns = [

    path('blog/<int:pk>/add/', CommentCreateView.as_view(), name='add_to_blog'),
]