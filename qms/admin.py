from django.contrib import admin
from .models import (
    Interaction,
    InteractionAssignmentLog,
    Investigation,
    InvestigationLog,
)


# =========================================================
# QMS INTERACTIONS
# =========================================================

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "interaction_type",
        "service_line",
        "severity",
        "status",
        "assigned_to",
        "logged_at",
    )

    list_filter = (
        "interaction_type",
        "service_line",
        "severity",
        "status",
    )

    search_fields = (
        "summary",
        "driver_name",
        "vehicle_reference",
        "route_reference",
    )

    readonly_fields = (
        "logged_at",
        "closed_at",
    )

    ordering = ("-logged_at",)

    fieldsets = (
        ("Classification", {
            "fields": (
                "interaction_type",
                "source",
                "service_line",
                "severity",
            )
        }),
        ("Details", {
            "fields": (
                "summary",
                "driver_name",
                "vehicle_reference",
                "route_reference",
                "occurred_at",
            )
        }),
        ("Management", {
            "fields": (
                "status",
                "assigned_to",
                "manager_notes",
                "closed_at",
            )
        }),
        ("Audit", {
            "fields": (
                "logged_by",
                "logged_at",
            )
        }),
    )


# =========================================================
# INTERACTION ASSIGNMENT AUDIT LOG
# =========================================================

@admin.register(InteractionAssignmentLog)
class InteractionAssignmentLogAdmin(admin.ModelAdmin):
    list_display = (
        "interaction",
        "previous_assignee",
        "new_assignee",
        "changed_by",
        "changed_at",
    )

    list_filter = (
        "changed_at",
        "changed_by",
    )

    search_fields = (
        "interaction__summary",
        "reason",
    )

    readonly_fields = (
        "interaction",
        "previous_assignee",
        "new_assignee",
        "changed_by",
        "reason",
        "changed_at",
    )

    ordering = ("-changed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# =========================================================
# FORMAL STAFF INVESTIGATIONS
# =========================================================

@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = (
        "case_number",
        "staff_member",
        "status",
        "created_at",
        "closed_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "case_number",
        "staff_member__username",
        "staff_member__first_name",
        "staff_member__last_name",
        "reason",
    )

    readonly_fields = (
        "case_number",
        "created_at",
        "closed_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Case Details", {
            "fields": (
                "case_number",
                "status",
            )
        }),
        ("Staff", {
            "fields": (
                "staff_member",
            )
        }),
        ("Investigation", {
            "fields": (
                "reason",
            )
        }),
        ("Audit", {
            "fields": (
                "created_by",
                "created_at",
                "closed_at",
            )
        }),
    )


# =========================================================
# INVESTIGATION AUDIT LOG (READ-ONLY)
# =========================================================

@admin.register(InvestigationLog)
class InvestigationLogAdmin(admin.ModelAdmin):
    list_display = (
        "investigation",
        "event_type",
        "performed_by",
        "created_at",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "investigation__case_number",
        "notes",
    )

    readonly_fields = (
        "investigation",
        "event_type",
        "performed_by",
        "notes",
        "created_at",
    )

    ordering = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
