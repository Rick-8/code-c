from django import forms
from .models import ControlledDocument
from .models import DocumentVersion


class PasswordConfirmForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
        })
    )


class DocumentEditForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ["content", "change_summary"]
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "form-control qms-input",
                "rows": 18,
                "placeholder": "Enter or update document content here..."
            }),
            "change_summary": forms.Textarea(attrs={
                "class": "form-control qms-input",
                "rows": 3,
                "placeholder": "Briefly describe what changed..."
            }),
        }


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


class DocumentStatusForm(forms.ModelForm):
    class Meta:
        model = ControlledDocument
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select qms-input"})
        }