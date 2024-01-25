import logging

from django.core.management.base import BaseCommand

from primed.users.audit import (
    AuditResults,
    drupal_data_study_site_audit,
    drupal_data_user_audit,
)

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

        user_audit_results = drupal_data_user_audit(apply_changes=should_update)
        print(f"User Audit Results {user_audit_results}")
        if user_audit_results.encountered_issues():
            print(
                user_audit_results.rows_by_result_type(
                    result_type=AuditResults.RESULT_TYPE_ISSUE
                )
            )

        site_audit_results = drupal_data_study_site_audit(apply_changes=should_update)
        print(f"Site Audit Results {site_audit_results}")
        if site_audit_results.encountered_issues():
            print(
                site_audit_results.rows_by_result_type(
                    result_type=AuditResults.RESULT_TYPE_ISSUE
                )
            )
