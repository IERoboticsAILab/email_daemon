from django.core.management.base import BaseCommand
from emails.email_daemon import EmailDaemon
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the email forwarding daemon'

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS('Initializing email daemon...'))
            daemon = EmailDaemon()
            self.stdout.write(self.style.SUCCESS('Email daemon started successfully!'))
            self.stdout.write(self.style.SUCCESS('Watching for emails from @cyphy.life...'))

            # Run the daemon
            daemon.run()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            logger.error(f"Daemon error: {str(e)}")
            raise
