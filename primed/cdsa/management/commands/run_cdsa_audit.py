from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse

from ...audit import signed_agreement_audit, workspace_audit


class Command(BaseCommand):
    help = "Run dbGaP access audit."

    def add_arguments(self, parser):
        email_group = parser.add_argument_group(title="Email reports")
        email_group.add_argument(
            "--email",
            help="""Email to which to send access reports that need action or have errors.""",
        )

    def _audit_signed_agreements(self):
        self.stdout.write("Running SignedAgreement access audit... ", ending="")
        data_access_audit = signed_agreement_audit.SignedAgreementAccessAudit()
        data_access_audit.run_audit()

        # Construct the url for handling errors.
        url = "https://" + Site.objects.get_current().domain + reverse("cdsa:audit:signed_agreements:sag:all")
        self._report_results(data_access_audit, url)
        self._send_email(data_access_audit, url)

    def _audit_workspaces(self):
        self.stdout.write("Running CDSAWorkspace access audit... ", ending="")
        data_access_audit = workspace_audit.WorkspaceAccessAudit()
        data_access_audit.run_audit()

        # Construct the url for handling errors.
        url = "https://" + Site.objects.get_current().domain + reverse("cdsa:audit:workspaces:all")
        self._report_results(data_access_audit, url)
        self._send_email(data_access_audit, url)

    def _report_results(self, data_access_audit, resolve_url):
        # Report errors and needs access.
        audit_ok = data_access_audit.ok()
        if audit_ok:
            self.stdout.write(self.style.SUCCESS("ok!"))
        else:
            self.stdout.write(self.style.ERROR("problems found."))

        # Print results
        self.stdout.write("* Verified: {}".format(len(data_access_audit.verified)))
        self.stdout.write("* Needs action: {}".format(len(data_access_audit.needs_action)))
        self.stdout.write("* Errors: {}".format(len(data_access_audit.errors)))

        if not audit_ok:
            self.stdout.write(self.style.ERROR(f"Please visit {resolve_url} to resolve these issues."))

    def _send_email(self, data_access_audit, url):
        # Send email if requested and there are problems.
        if not data_access_audit.ok():
            subject = "CDSA {} errors".format(data_access_audit.__class__.__name__)
            html_body = render_to_string(
                "primed_anvil/email_audit_report.html",
                context={
                    "title": subject,
                    "data_access_audit": data_access_audit,
                    "url": url,
                },
            )
            send_mail(
                subject,
                "Audit problems found. Please see attached report.",
                None,
                [self.email],
                fail_silently=False,
                html_message=html_body,
            )

    def handle(self, *args, **options):
        self.email = options["email"]
        self._audit_signed_agreements()
        self._audit_workspaces()
