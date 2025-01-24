from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import MailingList
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

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
