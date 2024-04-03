import logging

from django.core.management.base import BaseCommand
from django.utils.timezone import localtime

from primed.users import audit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync drupal user and domain data"
    NOTIFY_NONE = "none"
    NOTIFY_ALL = "all"
    NOTIFY_ISSUES = "issues"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update",
            action="store_true",
            dest="update",
            default=False,
            help="Make updates to sync local data with remote. If not set, will just report.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Log verbosely",
        )
        parser.add_argument(
            "--notify",
            dest="notify",
            choices=[self.NOTIFY_NONE, self.NOTIFY_ALL, self.NOTIFY_ISSUES],
            default=self.NOTIFY_ALL,
            help=f"Notification level: (default: {self.NOTIFY_ALL})",
        )

    def handle(self, *args, **options):
        apply_changes = options.get("update")
        be_verbose = options.get("verbose")
        # notify_type = options.get("notify")
        notification_content = f"Drupal data audit start: Applying Changes: {apply_changes} Start time: {localtime()}\n"
        site_audit = audit.SiteAudit(apply_changes=apply_changes)
        site_audit.run_audit()

        notification_content += (
            f"SiteAudit summary: status ok: {site_audit.ok()} verified: {len(site_audit.verified)} "
            f"needs_changes: {len(site_audit.needs_action)} errors: {len(site_audit.errors)}\n"
        )
        if site_audit.needs_action:
            notification_content += "Sites that need syncing:\n"
            notification_content += site_audit.get_needs_action_table().render_to_text()
        if site_audit.errors:
            notification_content += "Sites requiring intervention:\n"
            notification_content += site_audit.get_errors_table().render_to_text()

        if be_verbose:
            notification_content += site_audit.get_verified_table().render_to_text()

        user_audit = audit.UserAudit(apply_changes=apply_changes)
        user_audit.run_audit()
        notification_content += (
            "--------------------------------------\n"
            f"UserAudit summary: status ok: {user_audit.ok()} verified: {len(user_audit.verified)} "
            f"needs_changes: {len(user_audit.needs_action)} errors: {len(user_audit.errors)}\n"
        )
        if user_audit.needs_action:
            notification_content += "Users that need syncing:\n"
            notification_content += user_audit.get_needs_action_table().render_to_text()
        if user_audit.errors:
            notification_content += "Users that need intervention:\n"
            notification_content += user_audit.get_errors_table().render_to_text()
        if be_verbose:
            notification_content += user_audit.get_verified_table().render_to_text()

        self.stdout.write(notification_content)
