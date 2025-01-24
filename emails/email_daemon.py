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

    def check_emails(self):
        try:
            current_time = datetime.now()
            logger.info(f"Checking for new emails since {self.last_check}...")

            with imaplib.IMAP4_SSL(self.imap_server) as imap:
                imap.login(self.email, self.password)
                imap.select('INBOX')

                # Search for all emails, not just unseen
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
                                to_address = email_message['To']
                                logger.info(f"Processing new email sent to: {to_address}")

                                # Check if email was sent to any @cyphy.life address
                                if '@cyphy.life' in to_address:
                                    # Find corresponding mailing list
                                    mailing_list = MailingList.objects.filter(alias=to_address).first()

                                    if mailing_list:
                                        logger.info(f"Found mailing list for: {to_address}")
                                        subscribers = mailing_list.subscribers.filter(is_active=True)
                                        if subscribers:
                                            self.forward_email(email_message, subscribers, mailing_list)
                                            logger.info(f"Email forwarded to {len(subscribers)} subscribers")
                                        else:
                                            logger.warning(f"No active subscribers found for {to_address}")
                                    else:
                                        logger.info(f"No mailing list found for: {to_address}")
                                else:
                                    logger.info(f"Skipping email not sent to @cyphy.life")
                            else:
                                logger.debug(f"Skipping old email from {email_date}")
                        except Exception as e:
                            logger.error(f"Error processing email date: {str(e)}")
                            continue

            # Update last check time only after successful processing
            self.last_check = current_time
            logger.info(f"Email check completed. Next check will process emails after {self.last_check}")

        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")

    def forward_email(self, original_email, subscribers, mailing_list):
        try:
            logger.info("Starting email forwarding process")
            with smtplib.SMTP(self.smtp_server) as server:
                server.starttls()
                server.login(self.email, self.password)

                # Get original subject and add mailing list
                original_subject = original_email['Subject'] or ''
                list_name = mailing_list.alias.split('@')[0]  # Get 'msgs' from 'msgs@cyphy.life'
                new_subject = f"[{list_name.upper()}] {original_subject}"

                for subscriber in subscribers:
                    logger.info(f"Forwarding to: {subscriber.email}")
                    msg = MIMEMultipart()
                    msg['From'] = self.email
                    msg['To'] = subscriber.email
                    msg['Subject'] = new_subject
                    msg['Reply-To'] = original_email['From']

                    # Get email body
                    if original_email.is_multipart():
                        for part in original_email.walk():
                            if part.get_content_type() == "text/plain":
                                msg.attach(MIMEText(part.get_payload()))
                    else:
                        msg.attach(MIMEText(original_email.get_payload()))

                    server.send_message(msg)
                    logger.info(f"Successfully forwarded to {subscriber.email}")

        except Exception as e:
            logger.error(f"Error forwarding email: {str(e)}")

    def run(self):
        logger.info("Starting email daemon...")
        while True:
            self.check_emails()
            logger.info("Waiting 60 seconds before next check...")
            time.sleep(60)  # Check every minute
