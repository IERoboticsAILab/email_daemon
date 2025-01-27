from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import jwt
from datetime import datetime, timedelta

def send_subscription_confirmation(email, mailing_lists):
    subject = 'Subscription Confirmation - Cyphy.life Mailing Lists'
    lists_str = ", ".join([ml.alias for ml in mailing_lists])

    message = render_to_string('emails/subscription_email.html', {
        'email': email,
        'mailing_lists': mailing_lists,
    })

    send_mail(
        subject,
        message,
        settings.EMAIL_ADDRESS,
        [email],
        html_message=message,
    )

def generate_unsubscribe_token(email, list_id):
    """Generate a JWT token for unsubscribe confirmation"""
    payload = {
        'email': email,
        'list_id': list_id,
        'exp': datetime.utcnow() + timedelta(days=30)  # Token expires in 30 days
    }
    return jwt.encode(payload, str(settings.SECRET_KEY), algorithm='HS256')

def verify_unsubscribe_token(token):
    """Verify the unsubscribe token"""
    try:
        payload = jwt.decode(token, str(settings.SECRET_KEY), algorithms=['HS256'])
        return payload['email'], payload['list_id']
    except:
        return None, None

def send_unsubscribe_email(email, mailing_list):
    """Send email with unsubscribe confirmation link"""
    token = generate_unsubscribe_token(email, mailing_list.id)
    unsubscribe_link = f"{settings.SITE_URL}{reverse('unsubscribe_confirm')}?token={token}"

    subject = f'Unsubscribe Confirmation - {mailing_list.alias}'
    message = render_to_string('emails/unsubscribe_email.html', {
        'email': email,
        'mailing_list': mailing_list,
        'unsubscribe_link': unsubscribe_link,
    })

    send_mail(
        subject,
        message,
        settings.EMAIL_ADDRESS,
        [email],
        html_message=message,
    )
