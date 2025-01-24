import imaplib
import smtplib
from email import message_from_bytes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import time
import logging
from datetime import datetime, timedelta
import email.utils
from .models import MailingList

logger = logging.getLogger(__name__)

class EmailDaemon:
    def __init__(self):
        self.imap_server = settings.IMAP_SERVER
        self.smtp_server = settings.SMTP_SERVER
        self.email = settings.EMAIL_ADDRESS
        self.password = settings.EMAIL_PASSWORD
        self.last_check = datetime.now() - timedelta(minutes=1)
        logger.info(f"Email daemon initialized with email: {self.email}")

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
                imap.login(self.email, self.password)
                imap.select('INBOX')

                # Search for all emails
                _, message_numbers = imap.search(None, 'ALL')

                for num in message_numbers[0].split():
                    _, msg_data = imap.fetch(num, '(RFC822)')
                    email_body = msg_data[0][1]
                    email_message = message_from_bytes(email_body)

                    # Get email date
                    date_str = email_message['Date']
                    if date_str:
                        try:
                            email_date = datetime.fromtimestamp(
                                email.utils.mktime_tz(email.utils.parsedate_tz(date_str))
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

            # Update last check time only after successful processing
            self.last_check = current_time
            logger.info(f"Email check completed. Next check will process emails after {self.last_check}")

        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            logger.error("Error details:", exc_info=True)

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

    def forward_email(self, original_email, subscribers, mailing_list):
        try:
            logger.info("Starting email forwarding process")
            with smtplib.SMTP(self.smtp_server) as server:
                server.starttls()
                server.login(self.email, self.password)

                # Get original subject and add mailing list
                original_subject = original_email['Subject'] or ''
                list_name = mailing_list.alias.split('@')[0]
                new_subject = f"[{list_name.upper()}] {original_subject}"

                for subscriber in subscribers:
                    logger.info(f"Forwarding to: {subscriber.email}")
                    msg = MIMEMultipart('mixed')
                    msg['From'] = self.email
                    msg['To'] = subscriber.email
                    msg['Subject'] = new_subject
                    msg['Reply-To'] = original_email['From']

                    # Create the body of the message
                    body = MIMEMultipart('alternative')

                    # Variables to store the text and html parts
                    text_parts = []
                    html_parts = []

                    def process_part(part):
                        try:
                            content_type = part.get_content_type()
                            if content_type == 'text/plain':
                                text_parts.append(part.get_payload(decode=True).decode())
                            elif content_type == 'text/html':
                                html_parts.append(part.get_payload(decode=True).decode())
                            elif part.get_filename():
                                # Handle attachments by copying the entire part
                                msg.attach(part)
                        except Exception as e:
                            logger.error(f"Error processing email part: {str(e)}")
                            logger.error("Error details:", exc_info=True)

                    # Process the entire email structure
                    if original_email.is_multipart():
                        for part in original_email.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            process_part(part)
                    else:
                        process_part(original_email)

                    # Combine all text parts
                    if text_parts:
                        combined_text = '\n\n'.join(text_parts)
                        body.attach(MIMEText(combined_text, 'plain', 'utf-8'))

                    # Combine all HTML parts
                    if html_parts:
                        combined_html = '<br><br>'.join(html_parts)
                        body.attach(MIMEText(combined_html, 'html', 'utf-8'))

                    # If no content was found, use original payload
                    if not text_parts and not html_parts:
                        try:
                            payload = original_email.get_payload(decode=True)
                            if payload:
                                body.attach(MIMEText(payload.decode(), 'plain', 'utf-8'))
                        except Exception as e:
                            logger.error(f"Error handling fallback payload: {str(e)}")
                            logger.error("Error details:", exc_info=True)

                    # Attach the body to the message
                    msg.attach(body)

                    # Handle References and In-Reply-To headers properly
                    references = []
                    if 'References' in original_email:
                        references.extend(original_email['References'].split())
                    if 'Message-ID' in original_email:
                        references.append(original_email['Message-ID'])

                    if references:
                        msg['References'] = ' '.join(references)

                    if 'In-Reply-To' in original_email:
                        msg['In-Reply-To'] = original_email['In-Reply-To']

                    # Copy other important headers
                    for header in ['Date', 'Message-ID', 'Content-Type', 'Content-Transfer-Encoding']:
                        if header in original_email:
                            msg[header] = original_email[header]

                    try:
                        server.send_message(msg)
                        logger.info(f"Successfully forwarded to {subscriber.email}")
                    except Exception as e:
                        logger.error(f"Error sending email to {subscriber.email}: {str(e)}")
                        logger.error("Error details:", exc_info=True)

        except Exception as e:
            logger.error(f"Error forwarding email: {str(e)}")
            logger.error("Error details:", exc_info=True)

    def run(self):
        logger.info("Starting email daemon...")
        while True:
            self.check_emails()
            logger.info("Waiting 60 seconds before next check...")
            time.sleep(60)  # Check every minute
