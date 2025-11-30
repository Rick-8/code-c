from django.contrib import admin
from .models import Product, Order, OrderItem, ShopSettings


# =====================================================
# PRODUCT ADMIN
# =====================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "is_active",
        "is_staff_only",
        "allow_payroll_purchase",
    )
    list_filter = ("is_active", "is_staff_only", "allow_payroll_purchase")
    search_fields = ("title", "description")
    ordering = ("title",)


# =====================================================
# ORDER ITEM INLINE (Read-only inline for safety)
# =====================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "line_total")
    can_delete = False
    show_change_link = False


# =====================================================
# ORDER ADMIN
# =====================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "payment_method",
        "total_amount",
        "status",
    )

    list_filter = (
        "payment_method",
        "status",
        "created_at",
    )

    search_fields = ("id", "user__username", "stripe_payment_intent")

    ordering = ("-created_at",)

    inlines = [OrderItemInline]

    readonly_fields = (
        "user",
        "created_at",
        "payment_method",
        "total_amount",
        "stripe_payment_intent",
    )

    fieldsets = (
        ("Order Details", {
            "fields": (
                "user",
                "created_at",
                "payment_method",
                "total_amount",
                "status",
            )
        }),
        ("Stripe", {
            "fields": ("stripe_payment_intent",),
        }),
    )


# =====================================================
# SHOP SETTINGS (Singleton)
# =====================================================
@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ("is_shop_open", "ordering_enabled")

    def has_add_permission(self, request):
        """Prevent more than one settings object."""
        return not ShopSettings.objects.exists()
