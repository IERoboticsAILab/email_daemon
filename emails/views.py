from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
from .models import MailingList, Subscriber
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SubscriptionForm, UnsubscribeForm
from .utils import send_subscription_confirmation, send_unsubscribe_email, verify_unsubscribe_token

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

                # Send confirmation email
                send_subscription_confirmation(email, selected_lists)

                messages.success(request, 'Successfully subscribed! Please check your email for confirmation.')
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

            if not lists_to_unsubscribe:
                messages.error(request, 'Please select at least one list to unsubscribe from.')
                return redirect('mailing_lists')

            # Send unsubscribe confirmation email for each selected list
            for list_id in lists_to_unsubscribe:
                try:
                    mailing_list = MailingList.objects.get(id=list_id)
                    send_unsubscribe_email(email, mailing_list)
                except MailingList.DoesNotExist:
                    continue

            messages.success(request, 'Unsubscribe confirmation emails have been sent. Please check your inbox.')
            return redirect('mailing_lists')

    return render(request, 'emails/mailing_lists.html', {
        'form': SubscriptionForm(),
        'unsubscribe_form': UnsubscribeForm(),
        'mailing_lists': MailingList.objects.all(),
    })

@require_GET
def unsubscribe_confirm(request):
    token = request.GET.get('token')
    email, list_id = verify_unsubscribe_token(token)

    if email and list_id:
        try:
            subscriber = Subscriber.objects.get(email=email)
            mailing_list = MailingList.objects.get(id=list_id)
            subscriber.mailing_lists.remove(mailing_list)
            messages.success(request, f'Successfully unsubscribed from {mailing_list.alias}')
        except (Subscriber.DoesNotExist, MailingList.DoesNotExist):
            messages.error(request, 'Invalid unsubscribe request.')
    else:
        messages.error(request, 'Invalid or expired unsubscribe link.')

    return redirect('mailing_lists')
