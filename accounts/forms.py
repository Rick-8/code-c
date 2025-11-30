from allauth.account.forms import SignupForm
from django import forms

class CustomSignupForm(SignupForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    address_1 = forms.CharField(max_length=255, required=True)
    address_2 = forms.CharField(max_length=255, required=False)
    town = forms.CharField(max_length=100, required=True)
    postcode = forms.CharField(max_length=20, required=True)
    cv = forms.FileField(required=False)

    # Bootstrap form-control styling
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control",
                "style": "background:rgba(255,255,255,0.15); color:white; "
                         "border-radius:8px; border:1px solid rgba(255,255,255,0.2); padding:10px;"
            })

    def save(self, request):
        user = super().save(request)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data["phone"]
        user.address_1 = self.cleaned_data["address_1"]
        user.address_2 = self.cleaned_data["address_2"]
        user.town = self.cleaned_data["town"]
        user.postcode = self.cleaned_data["postcode"]
        user.cv = self.cleaned_data.get("cv")
        user.save()
        return user
