from django.urls import path
from django.shortcuts import redirect
from . import views


urlpatterns = [

    # =====================================================
    # QMS – Staff Logging
    # =====================================================
    path(
        "new/",
        views.create_interaction,
        name="qms_create"
    ),

    # =====================================================
    # QMS – Manager Views
    # =====================================================
    path(
        "manage/",
        views.qms_manager_list,
        name="qms_manager_list"
    ),
    path(
        "manage/<int:pk>/",
        views.qms_interaction_panel,
        name="qms_panel"
    ),
    path(
        "update/<int:pk>/",
        views.update_interaction,
        name="qms_update"
    ),

    # =====================================================
    # Investigations – Entry Point
    # =====================================================
    path(
        "investigations/",
        lambda request: redirect("investigation_dashboard"),
        name="investigations_root"
    ),

    # =====================================================
    # Investigations – Manager
    # =====================================================
    path(
        "investigations/dashboard/",
        views.investigation_dashboard,
        name="investigation_dashboard"
    ),
    path(
        "investigations/create/",
        views.investigation_create,
        name="investigation_create"
    ),
    path(
        "investigations/<int:pk>/",
        views.investigation_detail_manager,
        name="investigation_detail_manager"
    ),
    # Staff investigation views
    path(
        "investigations/my/",
        views.investigation_my_list,
        name="investigation_my_list"
    ),
    path(
        "investigations/my/<int:pk>/",
        views.investigation_staff_detail,
        name="investigation_staff_detail"
    ),
    path(
        "investigations/<int:pk>/add-log/",
        views.investigation_add_log,
        name="investigation_add_log",
    ),

]
