from django.urls import path
from .views import ContactCreateView, ContactListView

app_name = 'contact'

urlpatterns = [
    path('',     ContactCreateView.as_view(), name='contact'),
    path('admin/', ContactListView.as_view(),  name='contact_list'),
]
