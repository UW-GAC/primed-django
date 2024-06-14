from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse

from ...audit import access_audit, collaborator_audit


class Command(BaseCommand):
    help = "Run dbGaP access audit."

    def add_arguments(self, parser):
        email_group = parser.add_argument_group(title="Email reports")
        email_group.add_argument(
            "--email",
            help="""Email to which to send access reports that need action or have errors.""",
        )

    def run_access_audit(self, *args, **options):
        self.stdout.write("Running dbGaP access audit... ", ending="")
        audit = access_audit.dbGaPAccessAudit()
        audit.run_audit()
        self._handle_audit_results(audit, reverse("dbgap:audit:access:all"), **options)

    def run_collaborator_audit(self, *args, **options):
        self.stdout.write("Running dbGaP collaborator audit... ", ending="")
        audit = collaborator_audit.dbGaPCollaboratorAudit()
        audit.run_audit()
        self._handle_audit_results(audit, reverse("dbgap:audit:collaborators:all"), **options)

    def _handle_audit_results(self, audit, url, **options):
        # Report errors and needs access.
        audit_ok = audit.ok()
        # Construct the url for handling errors.
        url = "https://" + Site.objects.get_current().domain + url
        if audit_ok:
            self.stdout.write(self.style.SUCCESS("ok!"))
        else:
            self.stdout.write(self.style.ERROR("problems found."))

        # Print results
        self.stdout.write("* Verified: {}".format(len(audit.verified)))
        self.stdout.write("* Needs action: {}".format(len(audit.needs_action)))
        self.stdout.write("* Errors: {}".format(len(audit.errors)))

        if not audit_ok:
            self.stdout.write(self.style.ERROR(f"Please visit {url} to resolve these issues."))

            # Send email if requested and there are problems.
            email = options["email"]
            subject = "{} - problems found".format(audit.__class__.__name__)
            html_body = render_to_string(
                "primed_anvil/email_audit_report.html",
                context={
                    "title": "dbGaP collaborator audit",
                    "data_access_audit": audit,
                    "url": url,
                },
            )
            send_mail(
                subject,
                "Audit problems found. Please see attached report.",
                None,
                [email],
                fail_silently=False,
                html_message=html_body,
            )

    def handle(self, *args, **options):
        self.run_access_audit(*args, **options)
        self.run_collaborator_audit(*args, **options)
