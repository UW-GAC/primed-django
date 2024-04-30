import os

from django.core.management.base import BaseCommand, CommandError
from django_tables2.export.export import TableExport

from ... import helpers


class Command(BaseCommand):
    help = """Management command to generate CDSA records."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--outdir",
            help="""Output directory where reports should be written. This directory will be created.""",
            required=True,
        )

    def _export_table(self, table, filename):
        exporter = TableExport("tsv", table)
        with open(filename, "w") as f:
            f.write(exporter.export())

    def handle(self, *args, **options):
        # Create directory.
        outdir = options["outdir"]
        try:
            os.mkdir(outdir)
        except FileExistsError:
            raise CommandError("Directory already exists!")

        self.stdout.write("generating reports...", ending=" ")

        # Representatives.
        self._export_table(
            helpers.get_representative_records_table(),
            os.path.join(outdir, "representative_records.tsv"),
        )

        # Studies.
        self._export_table(helpers.get_study_records_table(), os.path.join(outdir, "study_records.tsv"))

        # CDSA workspaces.
        self._export_table(
            helpers.get_cdsa_workspace_records_table(),
            os.path.join(outdir, "workspace_records.tsv"),
        )

        # User access.
        self._export_table(
            helpers.get_user_access_records_table(),
            os.path.join(outdir, "useraccess_records.tsv"),
        )

        self.stdout.write(self.style.SUCCESS("done!"))
