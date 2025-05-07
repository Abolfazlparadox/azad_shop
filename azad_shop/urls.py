"""
URL configuration for azad_shop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path(
        'unit-admin/',
        include(('unit_admin.urls', 'unit_admin'), namespace='unit_admin')
    ),

    path('admin/', admin.site.urls),
    path('',include('home.urls')),
    path('blog/', include('blog.urls')),
    path('products/', include('product.urls')),
    path('accounts/', include('account.urls')),
    path('about/', include('about.urls')),

    path('cart/', include('cart.urls')),

    path('', include('comment.urls')),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)