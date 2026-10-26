"""Communications Django app configuration."""

import logging
import os
import sys
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _should_start_scheduler() -> bool:
    if os.environ.get("DISABLE_SCHEDULED_DISPATCH") == "1":
        return False
    if "test" in sys.argv:
        return False
    if "runserver" in sys.argv:
        return os.environ.get("RUN_MAIN") == "true"
    return os.environ.get("ENABLE_SCHEDULED_DISPATCH") == "1"


def _dispatch_loop():
    time.sleep(8)
    while True:
        try:
            from django.db import close_old_connections
            from apps.communications.services import CommunicationService

            close_old_connections()
            CommunicationService().dispatch_due_scheduled_messages()
        except Exception:
            logger.exception("Scheduled message dispatcher failed")
        time.sleep(15)


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.communications'
    verbose_name = 'Communications'

    def ready(self):
        if not _should_start_scheduler():
            return
        thread = threading.Thread(target=_dispatch_loop, name="scheduled-message-dispatcher", daemon=True)
        thread.start()
