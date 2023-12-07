import logging

from django.core.management.base import BaseCommand

from primed.users.audit import drupal_data_user_audit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync drupal user and domain data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            dest="update",
            default=False,
        )

    def handle(self, *args, **options):
        should_update = options.get("update")

        status = drupal_data_user_audit(should_update=should_update)
        print(f"Issues {status}")
