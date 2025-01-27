from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import MailingList, Subscriber
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SubscriptionForm

@csrf_exempt
def test_webhook(request):
    print("Test webhook endpoint hit!")
    return HttpResponse("Test webhook received!", status=200)

def test_email(request):
    """Test endpoint to verify email server configuration"""
    try:
        # Get the first mailing list for testing
        mailing_list = MailingList.objects.first()
        if not mailing_list:
            return HttpResponse("No mailing list found. Please create one first.", status=404)

        # Create test email
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_ADDRESS
        msg['To'] = mailing_list.alias
        msg['Subject'] = 'Test Email from Django'
        body = 'This is a test email from your mailing list system.'
        msg.attach(MIMEText(body, 'plain'))

        # Send test email
        with smtplib.SMTP(settings.SMTP_SERVER) as server:
            server.starttls()
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            server.send_message(msg)

        return HttpResponse("Test email sent successfully!")

    except Exception as e:
        return HttpResponse(f"Error sending test email: {str(e)}", status=500)

def mailing_lists(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            selected_lists = form.cleaned_data['mailing_lists']

            # Get or create subscriber
            subscriber, created = Subscriber.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )

            # Update subscriptions
            subscriber.mailing_lists.set(selected_lists)
            subscriber.is_active = True
            subscriber.save()

            messages.success(request, 'Your subscriptions have been updated!')
            return redirect('mailing_lists')
    else:
        form = SubscriptionForm()

    # Get all mailing lists with their subscribers
    mailing_lists = MailingList.objects.prefetch_related('subscribers')

    # If email is provided, get their current subscriptions
    email = request.GET.get('email')
    current_subscriptions = []
    if email:
        subscriber = Subscriber.objects.filter(email=email).first()
        if subscriber:
            current_subscriptions = list(subscriber.mailing_lists.values_list('id', flat=True))
            form = SubscriptionForm(initial={'email': email, 'mailing_lists': current_subscriptions})

    return render(request, 'emails/mailing_lists.html', {
        'form': form,
        'mailing_lists': mailing_lists,
        'current_subscriptions': current_subscriptions
    })
