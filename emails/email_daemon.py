import base64
import imaplib
import smtplib
from email import message_from_bytes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import django.db
import time
import logging
from datetime import datetime, timedelta
import email.utils
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from .models import MailingList

logger = logging.getLogger(__name__)

class EmailDaemon:
    def __init__(self):
        self.imap_server = settings.IMAP_SERVER
        self.smtp_server = settings.SMTP_SERVER
        self.email = settings.EMAIL_ADDRESS
        self.credentials = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
        )
        self.last_check = datetime.now() - timedelta(minutes=1)
        logger.info(f"Email daemon initialized with email: {self.email}")

    def _refresh_credentials(self):
        """Refresh the access token if needed."""
        if not self.credentials.valid:
            self.credentials.refresh(Request())

    def _xoauth2_bytes(self):
        """Return raw XOAUTH2 bytes for imaplib.authenticate() (imaplib base64-encodes itself)."""
        self._refresh_credentials()
        return f"user={self.email}\x01auth=Bearer {self.credentials.token}\x01\x01".encode()

    def _xoauth2_b64(self):
        """Return base64-encoded XOAUTH2 string for SMTP AUTH command."""
        self._refresh_credentials()
        auth_string = f"user={self.email}\x01auth=Bearer {self.credentials.token}\x01\x01"
        return base64.b64encode(auth_string.encode()).decode()

    def extract_email_addresses(self, email_message):
        """Extract all possible recipient addresses from various headers"""
        addresses = set()

        # Headers that might contain our target address
        recipient_headers = ['To', 'Delivered-To', 'X-Original-To', 'Envelope-To']

        for header in recipient_headers:
            header_value = email_message.get(header)
            if header_value:
                # Handle multiple addresses in one header
                for addr_part in header_value.split(','):
                    clean_addr = self.extract_email_address(addr_part)
                    if clean_addr:
                        addresses.add(clean_addr)

        logger.debug(f"Extracted addresses: {addresses}")
        return addresses

    def check_emails(self):
        try:
            current_time = datetime.now()
            logger.info(f"Checking for new emails since {self.last_check}...")

            with imaplib.IMAP4_SSL(self.imap_server) as imap:
                imap.authenticate('XOAUTH2', lambda _: self._xoauth2_bytes())
                imap.select('INBOX')

                # Server-side SINCE filter to only download recent emails
                date_str = self.last_check.strftime('%d-%b-%Y')
                _, message_numbers = imap.search(None, f'(SINCE "{date_str}")')

                for num in message_numbers[0].split():
                    _, msg_data = imap.fetch(num, '(RFC822)')
                    email_body = msg_data[0][1]
                    email_message = message_from_bytes(email_body)

                    # Get email date
                    date_header = email_message['Date']
                    if date_header:
                        try:
                            email_date = datetime.fromtimestamp(
                                email.utils.mktime_tz(email.utils.parsedate_tz(date_header))
                            )

                            # Only process emails newer than last check
                            if email_date > self.last_check:
                                # Get all possible recipient addresses
                                recipient_addresses = self.extract_email_addresses(email_message)
                                logger.info(f"Found recipient addresses: {recipient_addresses}")

                                # Check each address for @cyphy.life
                                for address in recipient_addresses:
                                    if '@cyphy.life' in address:
                                        # Find corresponding mailing list
                                        mailing_list = MailingList.objects.filter(alias=address).first()

                                        if mailing_list:
                                            logger.info(f"Found mailing list for: {address}")
                                            subscribers = mailing_list.subscribers.filter(is_active=True)
                                            if subscribers:
                                                self.forward_email(email_message, subscribers, mailing_list)
                                                logger.info(f"Email forwarded to {len(subscribers)} subscribers")
                                            else:
                                                logger.warning(f"No active subscribers found for {address}")
                                        else:
                                            logger.info(f"No mailing list found for: {address}")
                            else:
                                logger.debug(f"Skipping old email from {email_date}")
                        except Exception as e:
                            logger.error(f"Error processing email date: {str(e)}")
                            logger.error("Error details:", exc_info=True)
                            continue

                    # Free memory after processing each email
                    del email_message
                    del msg_data

            # Update last check time only after successful processing
            self.last_check = current_time
            logger.info(f"Email check completed. Next check will process emails after {self.last_check}")

        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            logger.error("Error details:", exc_info=True)
        finally:
            django.db.connections.close_all()

    def extract_email_address(self, address_string):
        """Extract email address from various formats like 'Name <email>' or '"email" <email>'"""
        if not address_string:
            return None

        addr = address_string.strip()
        # Check for <email> format
        if '<' in addr and '>' in addr:
            # Extract email between < and >
            start = addr.find('<') + 1
            end = addr.find('>')
            return addr[start:end].strip()
        # Otherwise return as is
        return addr.strip().strip('"')

    def _extract_parts(self, original_email):
        """Extract text, html, and attachment parts from an email once."""
        text_parts = []
        html_parts = []
        attachments = []

        def process_part(part):
            try:
                content_type = part.get_content_type()
                if content_type in ('text/plain', 'text/html'):
                    raw = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    decoded = raw.decode(charset, errors='replace')
                    if content_type == 'text/plain':
                        text_parts.append(decoded)
                    else:
                        html_parts.append(decoded)
                elif part.get_filename():
                    attachments.append(part)
            except Exception as e:
                logger.error(f"Error processing email part: {str(e)}")
                logger.error("Error details:", exc_info=True)

        if original_email.is_multipart():
            for part in original_email.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                process_part(part)
        else:
            process_part(original_email)

        return text_parts, html_parts, attachments

    def forward_email(self, original_email, subscribers, mailing_list):
        try:
            logger.info("Starting email forwarding process")

            # Parse body ONCE, reuse for all subscribers
            text_parts, html_parts, attachments = self._extract_parts(original_email)

            # Build combined text/html content once
            combined_text = '\n\n'.join(text_parts) if text_parts else None
            combined_html = '<br><br>'.join(html_parts) if html_parts else None

            # Fallback payload if no text or html found
            fallback_text = None
            if not text_parts and not html_parts:
                try:
                    payload = original_email.get_payload(decode=True)
                    if payload:
                        fallback_text = payload.decode()
                except Exception as e:
                    logger.error(f"Error handling fallback payload: {str(e)}")
                    logger.error("Error details:", exc_info=True)

            # Pre-compute shared header values
            original_subject = original_email['Subject'] or ''
            list_name = mailing_list.alias.split('@')[0]
            new_subject = f"[{list_name.upper()}] {original_subject}"

            references = []
            if 'References' in original_email:
                references.extend(original_email['References'].split())
            if 'Message-ID' in original_email:
                references.append(original_email['Message-ID'])

            with smtplib.SMTP(self.smtp_server, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.docmd('AUTH', 'XOAUTH2 ' + self._xoauth2_b64())

                for subscriber in subscribers:
                    logger.info(f"Forwarding to: {subscriber.email}")
                    msg = MIMEMultipart('mixed')
                    msg['From'] = mailing_list.alias
                    msg['To'] = subscriber.email
                    msg['Subject'] = new_subject
                    msg['Reply-To'] = mailing_list.alias

                    # Build the body
                    body = MIMEMultipart('alternative')

                    if combined_text:
                        body.attach(MIMEText(combined_text, 'plain', 'utf-8'))
                    if combined_html:
                        body.attach(MIMEText(combined_html, 'html', 'utf-8'))
                    if fallback_text:
                        body.attach(MIMEText(fallback_text, 'plain', 'utf-8'))

                    msg.attach(body)

                    # Attach files
                    for attachment in attachments:
                        msg.attach(attachment)

                    # Handle References and In-Reply-To headers
                    if references:
                        msg['References'] = ' '.join(references)

                    if 'In-Reply-To' in original_email:
                        msg['In-Reply-To'] = original_email['In-Reply-To']

                    # Preserve original send date (do not copy Content-Type/Content-Transfer-Encoding
                    # — those are managed by the MIME classes and must not be overwritten)
                    if 'Date' in original_email:
                        msg['Date'] = original_email['Date']

                    try:
                        server.send_message(msg)
                        logger.info(f"Successfully forwarded to {subscriber.email}")
                    except Exception as e:
                        logger.error(f"Error sending email to {subscriber.email}: {str(e)}")
                        logger.error("Error details:", exc_info=True)

                    del msg

        except Exception as e:
            logger.error(f"Error forwarding email: {str(e)}")
            logger.error("Error details:", exc_info=True)

    def run(self):
        logger.info("Starting email daemon...")
        while True:
            self.check_emails()
            logger.info("Waiting 60 seconds before next check...")
            time.sleep(60)  # Check every minute
