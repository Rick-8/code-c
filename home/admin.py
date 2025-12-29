from django.contrib import admin
from .models import LiveOpsCredential, OpsRoute, OpsJourney


@admin.register(LiveOpsCredential)
class LiveOpsCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "granted_at", "granted_by")
    list_filter = ("is_enabled",)
    search_fields = ("user__username", "user__email")


@admin.register(OpsRoute)
class OpsRouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "origin", "destination", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "origin", "destination")
    ordering = ("code",)


@admin.register(OpsJourney)
class OpsJourneyAdmin(admin.ModelAdmin):
    list_display = ("route", "service_date", "planned_departure", "status", "delay_minutes", "updated_at", "updated_by")
    list_filter = ("status", "service_date")
    search_fields = ("route__code", "route__name", "reason")
    autocomplete_fields = ("route", "updated_by")
