# urls.py

from django.urls import path
from .views import (
    UserListView,
    UserCreateView,
    RoleListView,
    RoleCreateView,
    RoleDeleteView, UnitAdminIndexView, get_cities, UserUpdateView, RoleUpdateView, AddressListView,
    AddressCreateView, AddressUpdateView, AddressDeleteView, ProductListView, ProductCreateView,
    ProductSoftDeleteView, ProductHardDeleteView, CategoryListView, CategoryCreateView, CategoryUpdateView,
    CategorySoftDeleteView, CategoryHardDeleteView, UserSoftDeleteView, UserHardDeleteView, AdminSettingsView,
    AdminAddressDeleteView, ContactMessageListView, ContactMessageAnswerView,
)

app_name = 'unit_admin'
urlpatterns = [
    path('', UnitAdminIndexView.as_view(), name='admin_index'),
    # کاربران
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/add/', UserCreateView.as_view(), name='add_user'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/soft-delete/', UserSoftDeleteView.as_view(), name='user_soft_delete'),
    path('users/<int:pk>/hard-delete/', UserHardDeleteView.as_view(), name='user_hard_delete'),
    # نقش‌ها
    path('roles/', RoleListView.as_view(), name='role_list'),
    path('roles/add/', RoleCreateView.as_view(), name='add_role'),
    path('roles/<int:pk>/edit/', RoleUpdateView.as_view(), name='role_edit'),
    path('roles/<int:pk>/delete/',RoleDeleteView.as_view(),name='delete_role'),
    # شهرها
    path('cities/options/', get_cities, name='city_options'),
    #addresses
    path('addresses/', AddressListView.as_view(), name='address_list'),
    path('addresses/add/', AddressCreateView.as_view(), name='address_add'),
    path('addresses/<int:pk>/edit/', AddressUpdateView.as_view(), name='address_edit'),
    path('addresses/<int:pk>/delete/', AddressDeleteView.as_view(), name='delete_address'),

    #products
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/add/', ProductCreateView.as_view(), name='product_add'),
    # Soft delete via POST from a button/form
    path('products/<int:pk>/delete/', ProductSoftDeleteView.as_view(), name='product_soft_delete'),
    # Hard delete (if you ever need it)
    path('products/<int:pk>/hard-delete/', ProductHardDeleteView.as_view(), name='product_hard_delete'),

    path('categories/',              CategoryListView.as_view(),       name='category_list'),
    path('categories/add/',          CategoryCreateView.as_view(),     name='category_add'),
    path('categories/<int:pk>/edit/',CategoryUpdateView.as_view(),     name='category_edit'),
    path('categories/<int:pk>/delete/',     CategorySoftDeleteView.as_view(), name='category_soft_delete'),
    path('categories/<int:pk>/hard-delete/',CategoryHardDeleteView.as_view(), name='category_hard_delete'),

    path('settings/', AdminSettingsView.as_view(), name='settings'),
    path('settings/address/<int:pk>/delete/',AdminAddressDeleteView.as_view(),name='settings_address_delete'),

    path("contact/", ContactMessageListView.as_view(), name="contact_list"),
    path("contact/<int:pk>/answer/", ContactMessageAnswerView.as_view(), name="contact_answer"),
]
