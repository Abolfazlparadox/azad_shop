# blog/urls.py
from django.urls import path
    # wherever you defined it
from .views import  CommentCreateGenericView

app_name = 'comment'

urlpatterns = [

    path(
        'add/<str:app_label>/<str:model_name>/<int:object_id>/',
        CommentCreateGenericView.as_view(),
        name='add_generic'
    ),
]