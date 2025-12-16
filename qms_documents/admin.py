from django.contrib import admin
from .models import ControlledDocument, DocumentVersion


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    can_delete = False
    readonly_fields = (
        "version_major",
        "version_minor",
        "content",
        "change_summary",
        "created_by",
        "created_at",
        "is_current",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ControlledDocument)
class ControlledDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "title",
        "category",
        "status",
        "created_at",
    )
    search_fields = ("reference", "title")
    list_filter = ("status", "category")
    ordering = ("reference",)
    readonly_fields = ("created_at",)

    inlines = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "version_major",
        "version_minor",
        "is_current",
        "created_by",
        "created_at",
    )
    list_filter = ("is_current", "created_by")
    search_fields = ("document__reference",)
    ordering = ("-created_at",)

    readonly_fields = (
        "document",
        "version_major",
        "version_minor",
        "content",
        "change_summary",
        "created_by",
        "created_at",
        "is_current",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
