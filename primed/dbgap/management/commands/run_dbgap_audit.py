from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse

from ... import audit


class Command(BaseCommand):
    help = "Run dbGaP access audit."

    def add_arguments(self, parser):
        email_group = parser.add_argument_group(title="Email reports")
        email_group.add_argument(
            "--email",
            help="""Email to which to send access reports that need action or have errors.""",
        )

    def handle(self, *args, **options):
        self.stdout.write("Running dbGaP access audit... ", ending="")
        data_access_audit = audit.dbGaPAccessAudit()
        data_access_audit.run_audit()

        # Report errors and needs access.
        audit_ok = data_access_audit.ok()
        # Construct the url for handling errors.
        url = (
            "https://" + Site.objects.get_current().domain + reverse("dbgap:audit:all")
        )
        if audit_ok:
            self.stdout.write(self.style.SUCCESS("ok!"))
        else:
            self.stdout.write(self.style.ERROR("problems found."))

        # Print results
        self.stdout.write("* Verified: {}".format(len(data_access_audit.verified)))
        self.stdout.write(
            "* Needs action: {}".format(len(data_access_audit.needs_action))
        )
        self.stdout.write("* Errors: {}".format(len(data_access_audit.errors)))

        if not audit_ok:
            self.stdout.write(
                self.style.ERROR(f"Please visit {url} to resolve these issues.")
            )

            # Send email if requested and there are problems.
            email = options["email"]
            subject = "dbGaP access audit - problems found"
            html_body = render_to_string(
                "dbgap/email_audit_report.html",
                context={
                    "data_access_audit": data_access_audit,
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
