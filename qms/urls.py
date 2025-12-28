from django.urls import path
from django.shortcuts import redirect

from . import views
from .views import qms_dashboard


urlpatterns = [

    # =====================================================
    # QMS – Staff Logging
    # =====================================================
    path(
        "new/",
        views.create_interaction,
        name="qms_interaction_create",  # FIXED (matches templates)
    ),

    # =====================================================
    # QMS – Manager Views
    # =====================================================
    path(
        "manage/",
        views.qms_manager_list,
        name="qms_manager_list",
    ),
    path(
        "manage/<int:pk>/",
        views.qms_interaction_panel,
        name="qms_panel",
    ),
    path(
        "update/<int:pk>/",
        views.update_interaction,
        name="qms_update",
    ),

    # =====================================================
    # Investigations – Entry Point
    # =====================================================
    path(
        "investigations/",
        lambda request: redirect("investigation_dashboard"),
        name="investigations_root",
    ),

    # =====================================================
    # Investigations – Manager
    # =====================================================
    path(
        "investigations/dashboard/",
        views.investigation_dashboard,
        name="investigation_dashboard",
    ),
    path(
        "investigations/create/",
        views.investigation_create,
        name="investigation_create",
    ),
    path(
        "investigations/<int:pk>/",
        views.investigation_detail_manager,
        name="investigation_detail_manager",
    ),

    # =====================================================
    # Investigations – Staff
    # =====================================================
    path(
        "investigations/my/",
        views.investigation_my_list,
        name="investigation_my_list",
    ),
    path(
        "investigations/my/<int:pk>/",
        views.investigation_staff_detail,
        name="investigation_staff_detail",
    ),
    path(
        "investigations/<int:pk>/add-log/",
        views.investigation_add_log,
        name="investigation_add_log",
    ),

    # =====================================================
    # QMS – Primary Authority Confirmation
    # =====================================================
    path(
        "confirm-primary/",
        views.confirm_primary_authority,
        name="qms_confirm_primary",
    ),

    # =====================================================
    # QMS – Dashboard (root)
    # =====================================================
    path(
        "",
        qms_dashboard,
        name="qms_dashboard",
    ),
    # =====================================================
    # QMS – Primary Governance
    # =====================================================
    path(
        "primary/",
        views.qms_primary_list,
        name="qms_primary_list",
    ),

    path(
        "responsibilities/",
        views.responsibility_register,
        name="responsibility_register",
    ),
    path(
        "responsibilities/read-only/",
        views.responsibility_register_readonly,
        name="responsibility_register_readonly",
    ),
    path(
        "primary/appoint/",
        views.appoint_primary_authority,
        name="appoint_primary_authority",
    ),
    path(
        "primary/revoke/<int:authority_id>/",
        views.revoke_primary_authority,
        name="qms_revoke_primary",
    ),
    path(
        "responsibilities/add/",
        views.responsibility_create,
        name="responsibility_create",
    ),


]
