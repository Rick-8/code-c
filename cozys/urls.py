from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home page
    path(
        "",
        TemplateView.as_view(template_name="home/home.html"),
        name="home",
    ),

    # Apps
    path("", include("home.urls")),
    path("academy/", include("academy.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("shop/", include("shop.urls")),
    path("qms/", include("qms.urls")),
    path("qms-documents/", include("qms_documents.urls")),
]
