from django.core.management.base import BaseCommand
from apps.communications.services import CommunicationService


class Command(BaseCommand):
    help = "Dispatch scheduled messages whose send time has arrived."

    def handle(self, *args, **options):
        outcomes = CommunicationService().dispatch_due_scheduled_messages()
        self.stdout.write(self.style.SUCCESS(f"Dispatched {len(outcomes)} scheduled message(s)."))
