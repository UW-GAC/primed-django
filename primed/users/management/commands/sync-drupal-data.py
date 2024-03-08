import logging

from django.core.management.base import BaseCommand

from primed.users.audit import drupal_data_study_site_audit, drupal_data_user_audit

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
        notify_type = options.get("notify")

        site_audit_results = drupal_data_study_site_audit(apply_changes=apply_changes)
        logger.info(
            f"Site Audit (Update: {apply_changes}) Results summary: {site_audit_results}"
        )
        detailed_site_audit_results = site_audit_results.detailed_results()

        user_audit_results = drupal_data_user_audit(apply_changes=apply_changes)
        logger.info(
            f"User Audit (Update: {apply_changes}) Results summary: {user_audit_results}"
        )
        detailed_user_audit_results = user_audit_results.detailed_results()

        if be_verbose:
            logger.debug(
                f"User Audit Results:\n{user_audit_results.detailed_results()}"
            )
            logger.debug(
                f"Study Site Audit Results:\n{site_audit_results.detailed_results()}"
            )

        notification_content = ""
        if user_audit_results.encountered_issues():
            notification_content += "Encountered user audit issues:\n"
            notification_content += user_audit_results.detailed_issues()
        else:
            notification_content += "No user audit issues.\n"

        if site_audit_results.encountered_issues():
            notification_content += "Encountered site audit issues:\n"
            notification_content += site_audit_results.detailed_issues()
        else:
            notification_content += "No site audit issues.\n"

        if notify_type == self.NOTIFY_ALL:
            notification_content += detailed_site_audit_results
            notification_content += detailed_user_audit_results
        notification_content += "sync-drupal-data audit complete\n"

        self.stdout.write(notification_content)
