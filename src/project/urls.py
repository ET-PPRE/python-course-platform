"""
URL configuration for project project.

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
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.shortcuts import render
from debug_toolbar.toolbar import debug_toolbar_urls
from pathlib import Path
from django.http import HttpResponseForbidden
from site_data.models import HomepageContent
from django.conf import settings
from django.conf.urls.static import static
from site_data.views import tinymce_image_upload

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BOOK_PATH = PROJECT_DIR / "python_course_repo" / "book" / "_build" / "html"

def home_view(request):
    homepage_content = HomepageContent.objects.first()
    return render(request, "home.html", {
        "homepage_content": homepage_content
    })

# def home_view(request):
#     return render(request, "home.html")

def signup_disabled(request):
    return HttpResponseForbidden("Signup is disabled. Please contact the administrator.")

urlpatterns = [
    path("__reload__/", include("django_browser_reload.urls")),
    path('admin/', admin.site.urls),
    path("accounts/signup/", signup_disabled, name="account_signup"),
    path("accounts/", include("allauth.urls")),
    path('tinymce/', include('tinymce.urls')),
    path("tinymce-upload/", tinymce_image_upload, name="tinymce_image_upload"),
    path("", home_view, name="home"),
    path('assignments/', include('assignments.urls', namespace='assignments')),
    path("", include("grader.urls", namespace='grader')),
    re_path(
        r"^book/(?P<path>.*)$",
        serve,
        {"document_root": str(BOOK_PATH)},
        name="jupyterbook"
    ),
] + debug_toolbar_urls() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
