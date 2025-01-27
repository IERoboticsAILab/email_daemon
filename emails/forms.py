from django import forms
from .models import MailingList

class SubscriptionForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    mailing_lists = forms.ModelMultipleChoiceField(
        queryset=MailingList.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select lists to subscribe to:'
    )

class UnsubscribeForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
