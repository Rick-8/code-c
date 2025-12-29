from django import forms
from .models import OpsRoute, OpsJourney


class OpsRouteForm(forms.ModelForm):
    class Meta:
        model = OpsRoute
        fields = ["code", "name", "origin", "destination", "is_active"]


class OpsJourneyForm(forms.ModelForm):
    class Meta:
        model = OpsJourney
        fields = ["route", "service_date", "planned_departure", "status", "delay_minutes", "reason"]
