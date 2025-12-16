from django.urls import path
from . import views

urlpatterns = [
    # CREATE
    path("add/", views.document_create, name="document_create"),

    # EDIT FLOW (explicit first)
    path("<str:reference>/confirm-edit/", views.confirm_edit, name="confirm_edit"),
    path("<str:reference>/edit/", views.document_edit, name="document_edit"),

    # HISTORIC VERSION VIEW
    path(
        "<str:reference>/version/<int:major>/<int:minor>/",
        views.document_version_detail,
        name="document_version_detail",
    ),

    # LIST + DETAIL (LAST)
    path("", views.document_list, name="document_list"),
    path("<str:reference>/", views.document_detail, name="document_detail"),
]
