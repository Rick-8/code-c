from django.db import models
from django.conf import settings
from decimal import Decimal


# -------------------------------------------------------------
# PRODUCT MODEL
# -------------------------------------------------------------
class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="shop/", blank=True, null=True)

    is_staff_only = models.BooleanField(default=False)   # staff can purchase only
    is_active = models.BooleanField(default=True)
    allow_payroll_purchase = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


# -------------------------------------------------------------
# SHOP SETTINGS (Singleton)
# -------------------------------------------------------------
class ShopSettings(models.Model):
    is_shop_open = models.BooleanField(default=True)  # shop visible/hidden
    ordering_enabled = models.BooleanField(default=True)  # basket/checkout allowed

    class Meta:
        verbose_name = "Shop Settings"

    def __str__(self):
        return "Shop Configuration"


# -------------------------------------------------------------
# ORDER MODEL
# -------------------------------------------------------------
class Order(models.Model):
    PAYMENT_METHODS = (
        ("card", "Card Payment"),
        ("payroll", "Deduct from Next Pay"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending Payment"),
        ("PAID", "Paid"),
        ("DISPATCHED", "Dispatched / Sent"),
        ("COLLECTED", "Collected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)

    # Track order progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    # Stripe integration
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} ({self.get_status_display()})"

    class Meta:
        ordering = ["-created_at"]


# -------------------------------------------------------------
# ORDER ITEM MODEL
# -------------------------------------------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    line_total = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.product.title}"
