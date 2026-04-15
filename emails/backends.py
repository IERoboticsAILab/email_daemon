import base64
import smtplib

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class GmailOAuth2Backend(BaseEmailBackend):
    """
    Django email backend that authenticates to Gmail SMTP using OAuth2 XOAUTH2.
    Reads GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN from settings.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.connection = None
        self._credentials = None

    def _get_credentials(self):
        if self._credentials is None:
            self._credentials = Credentials(
                token=None,
                refresh_token=settings.GMAIL_REFRESH_TOKEN,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=settings.GMAIL_CLIENT_ID,
                client_secret=settings.GMAIL_CLIENT_SECRET,
            )
        if not self._credentials.valid:
            self._credentials.refresh(Request())
        return self._credentials

    def open(self):
        if self.connection:
            return False
        try:
            self.connection = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            self.connection.ehlo()
            self.connection.starttls()
            self.connection.ehlo()
            creds = self._get_credentials()
            auth_string = (
                f"user={settings.EMAIL_HOST_USER}"
                f"\x01auth=Bearer {creds.token}\x01\x01"
            )
            self.connection.docmd(
                'AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string.encode()).decode()
            )
            return True
        except Exception:
            if not self.fail_silently:
                raise

    def close(self):
        if self.connection is None:
            return
        try:
            self.connection.quit()
        except smtplib.SMTPException:
            try:
                self.connection.close()
            except Exception:
                pass
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        new_conn_created = self.open()
        if not self.connection:
            return 0
        num_sent = 0
        for message in email_messages:
            try:
                encoding = message.encoding or settings.DEFAULT_CHARSET
                from_email = sanitize_address(message.from_email, encoding)
                recipients = [
                    sanitize_address(addr, encoding)
                    for addr in message.recipients()
                ]
                self.connection.sendmail(
                    from_email, recipients, message.message().as_bytes(linesep='\r\n')
                )
                num_sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        if new_conn_created:
            self.close()
        return num_sent
