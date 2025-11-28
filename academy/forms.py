from django import forms
from .models import Question, Choice


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
        }


ChoiceFormSet = forms.inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    extra=4,        # number of answer boxes that appear
    can_delete=True
)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['module', 'text', 'order']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control'}),
            'module': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
