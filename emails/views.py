from django.http import HttpResponse, JsonResponse
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
from .forms import SubscriptionForm, UnsubscribeForm

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
        action = request.POST.get('action')

        if action == 'subscribe':
            form = SubscriptionForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                selected_lists = form.cleaned_data['mailing_lists']

                subscriber, created = Subscriber.objects.get_or_create(
                    email=email,
                    defaults={'is_active': True}
                )

                subscriber.mailing_lists.add(*selected_lists)
                subscriber.is_active = True
                subscriber.save()

                messages.success(request, 'Successfully subscribed to the selected mailing lists!')
                return redirect('mailing_lists')

        elif action == 'check':
            email = request.POST.get('email')
            subscriber = Subscriber.objects.filter(email=email).first()
            if subscriber:
                user_subscriptions = subscriber.mailing_lists.all()
                return render(request, 'emails/mailing_lists.html', {
                    'form': SubscriptionForm(),
                    'unsubscribe_form': UnsubscribeForm(initial={'email': email}),
                    'mailing_lists': MailingList.objects.all(),
                    'user_subscriptions': user_subscriptions,
                    'checked_email': email
                })
            else:
                messages.info(request, 'No subscriptions found for this email address.')

        elif action == 'unsubscribe':
            email = request.POST.get('email')
            lists_to_unsubscribe = request.POST.getlist('unsubscribe_from')

            subscriber = Subscriber.objects.filter(email=email).first()
            if subscriber and lists_to_unsubscribe:
                subscriber.mailing_lists.remove(*lists_to_unsubscribe)
                messages.success(request, 'Successfully unsubscribed from the selected lists.')
            return redirect('mailing_lists')

    return render(request, 'emails/mailing_lists.html', {
        'form': SubscriptionForm(),
        'unsubscribe_form': UnsubscribeForm(),
        'mailing_lists': MailingList.objects.all(),
    })
