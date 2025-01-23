from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import MailingList
import resend

#  Resend API key
resend.api_key = 'resend_api_key'

@csrf_exempt
@require_POST
def handle_incoming_email(request):
    try:
        data = json.loads(request.body)
        to_address = data.get('to', '').lower()
        from_address = data.get('from', '')
        subject = data.get('subject', '')
        text = data.get('text', '')
        html = data.get('html', '')

        # Find the corresponding mailing list
        mailing_list = MailingList.objects.filter(alias=to_address).first()

        if mailing_list:
            # Get all active subscribers
            subscribers = mailing_list.subscribers.filter(is_active=True)

            # Forward the email to all subscribers
            for subscriber in subscribers:
                resend.Emails.send({
                    "from": f"Robotics Lab <{to_address}>",
                    "to": subscriber.email,
                    "subject": subject,
                    "html": html or text,
                    "reply_to": from_address,
                })

            return HttpResponse("Email forwarded successfully", status=200)

        return HttpResponse("Mailing list not found", status=404)

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
