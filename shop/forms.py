from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "title",
            "description",
            "price",
            "image",
            "is_staff_only",
            "is_active",
            "allow_payroll_purchase",
        ]
