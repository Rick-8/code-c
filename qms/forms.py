from django import forms
from .models import Interaction
from django.contrib.auth import get_user_model

User = get_user_model()


class AppointPrimaryAuthorityForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by(
            "last_name", "first_name"
        ),
        label="Select user",
        help_text="Choose an existing active user to appoint as Primary QMS Authority."
    )


class InteractionForm(forms.ModelForm):
    occurred_at = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg bg-dark text-light border-secondary'
            }
        )
    )

    class Meta:
        model = Interaction
        fields = [
            'interaction_type',
            'source',
            'service_line',
            'occurred_at',
            'severity',
            'summary',
            'driver_name',
            'vehicle_reference',
            'route_reference',
        ]

        widgets = {
            'interaction_type': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary'
            }),
            'source': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary'
            }),
            'service_line': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary'
            }),
            'severity': forms.Select(attrs={
                'class': 'form-select bg-dark text-light border-secondary'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control bg-dark text-light border-secondary',
                'rows': 4
            }),
            'driver_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary'
            }),
            'vehicle_reference': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary'
            }),
            'route_reference': forms.TextInput(attrs={
                'class': 'form-control bg-dark text-light border-secondary'
            }),
        }
