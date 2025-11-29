from django.db import models
from django.conf import settings


class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="shop/", blank=True, null=True)
    is_staff_only = models.BooleanField(default=False)   # <-- staff purchase only
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class ShopSettings(models.Model):
    is_shop_open = models.BooleanField(default=True)   # shop visible or hidden
    ordering_enabled = models.BooleanField(default=True)  # basket/checkout allowed

    class Meta:
        verbose_name = "Shop Settings"

    def __str__(self):
        return "Shop Configuration"
