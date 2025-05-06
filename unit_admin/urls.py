# urls.py

from django.urls import path
from .views import (
    UserListView,
    UserCreateView,
    RoleListView,
    RoleCreateView,
    RoleDeleteView, UserDeleteView, UnitAdminIndexView, get_cities,
)

app_name = 'unit_admin'
urlpatterns = [
    path('', UnitAdminIndexView.as_view(), name='admin_index'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/add/', UserCreateView.as_view(), name='add_user'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('roles/add/', RoleCreateView.as_view(), name='add_role'),
    path('roles/delete/', RoleDeleteView.as_view(), name='delete_role'),
    path('get-cities/', get_cities, name='get_cities'),

]
