from django import forms
from .models import MailingList

class SubscriptionForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    mailing_lists = forms.ModelMultipleChoiceField(
        queryset=MailingList.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
