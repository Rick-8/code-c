from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "is_staff_only", "is_active")
    list_editable = ("is_staff_only", "is_active")
    search_fields = ("title", "description")
    list_filter = ("is_staff_only", "is_active")
