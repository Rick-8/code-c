from django import forms
from .models import ControlledDocument


class PasswordConfirmForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
        })
    )


class DocumentEditForm(forms.Form):
    change_summary = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Describe what changed and why",
        })
    )

    content = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 18,
        })
    )


class ControlledDocumentCreateForm(forms.ModelForm):
    class Meta:
        model = ControlledDocument
        fields = ["reference", "title", "category", "status"]
        widgets = {
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
