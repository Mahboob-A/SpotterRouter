"""
URL configuration for fuel_router project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/favicons/favicon.ico", permanent=True),
        name="favicon",
    ),
    path(
        "apple-touch-icon.png",
        RedirectView.as_view(
            url="/static/favicons/apple-touch-icon.png", permanent=True
        ),
        name="apple-touch-icon",
    ),
    path(
        "apple-touch-icon-precomposed.png",
        RedirectView.as_view(
            url="/static/favicons/apple-touch-icon.png", permanent=True
        ),
        name="apple-touch-icon-precomposed",
    ),
    path(
        "site.webmanifest",
        RedirectView.as_view(
            url="/static/favicons/site.webmanifest", permanent=True
        ),
        name="site-webmanifest",
    ),
    path(
        "manifest.json",
        RedirectView.as_view(
            url="/static/favicons/site.webmanifest", permanent=True
        ),
        name="manifest-json",
    ),
    re_path(
        r"^(?P<icon>favicon-\d+x\d+\.png)$",
        RedirectView.as_view(url="/static/favicons/%(icon)s", permanent=True),
        name="favicon-resolution-icon",
    ),
    path("api/", include("api.urls")),
    path("", include("ui.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

