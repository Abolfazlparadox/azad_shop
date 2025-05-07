# urls.py

from django.urls import path
from .views import (
    UserListView,
    UserCreateView,
    RoleListView,
    RoleCreateView,
    RoleDeleteView, UserDeleteView, UnitAdminIndexView, get_cities, UserUpdateView, RoleUpdateView, AddressListView,
    AddressCreateView, AddressUpdateView, AddressDeleteView,
)

app_name = 'unit_admin'
urlpatterns = [
    path('', UnitAdminIndexView.as_view(), name='admin_index'),
    # کاربران
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/add/', UserCreateView.as_view(), name='add_user'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),
    # نقش‌ها
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('roles/add/', RoleCreateView.as_view(), name='add_role'),
    path('roles/<int:pk>/edit/', RoleUpdateView.as_view(), name='role_edit'),
    path('roles/delete/', RoleDeleteView.as_view(), name='delete_role'),
    # شهرها
    path('cities/options/', get_cities, name='city_options'),
    #addresses
    path('addresses/', AddressListView.as_view(), name='address_list'),
    path('addresses/add/', AddressCreateView.as_view(), name='address_add'),
    path('addresses/<int:pk>/edit/', AddressUpdateView.as_view(), name='address_edit'),
    path('addresses/<int:pk>/delete/', AddressDeleteView.as_view(), name='address_delete'),
]
