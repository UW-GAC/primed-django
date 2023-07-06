"""Tests for management commands in the `cdsa` app."""

import os
import tempfile
from io import StringIO
from os.path import isdir, isfile

from django.core.management import CommandError, call_command
from django.test import TestCase

from ..tests import factories


class CDSARecordsTest(TestCase):
    """Tests for the records_report command."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.outdir = os.path.join(self.tmpdir.name, "test_output")

    def test_output(self):
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        self.assertIn("generating reports... done!", out.getvalue())

    def test_files_created(self):
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        self.assertTrue(isdir(self.outdir))
        self.assertTrue(isfile(os.path.join(self.outdir, "representative_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "study_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "workspace_records.tsv")))
        self.assertTrue(isfile(os.path.join(self.outdir, "useraccess_records.tsv")))

    def test_representative_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "representative_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_representative_records_three(self):
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "representative_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 4)

    def test_study_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "study_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_study_records_one(self):
        factories.DataAffiliateAgreementFactory.create(
            signed_agreement__is_primary=True
        )
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "study_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_cdsa_workspace_records_zero(self):
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "workspace_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    def test_cdsa_workspace_records_one(self):
        factories.CDSAWorkspaceFactory.create()
        out = StringIO()
        call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        with open(os.path.join(self.outdir, "workspace_records.tsv")) as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_directory_exists(self):
        os.mkdir(self.outdir)
        out = StringIO()
        with self.assertRaises(CommandError) as e:
            call_command("cdsa_records", self.outdir, "--no-color", stdout=out)
        self.assertIn("already exists", str(e.exception))
