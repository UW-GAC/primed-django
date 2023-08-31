"""Tests for data migrations in the app."""
from datetime import date

from anvil_consortium_manager.tests.factories import BillingProjectFactory, WorkspaceFactory
from django_test_migrations.contrib.unittest_case import MigratorTestCase
import factory

from . import factories

class PopulateAgreementMajorVersionTest(MigratorTestCase):
    """Tests for the populate_agreement_major_version migration."""

    migrate_from = ("cdsa", "0003_agreementversion_add_major_version_fk")
    migrate_to = ("cdsa", "0004_populate_agreementmajorversion")

    def prepare(self):
        """Prepare some data before the migration."""
        # Get model definition for the old state.
        AgreementVersion = self.old_state.apps.get_model("cdsa", "AgreementVersion")
        # Populate with multiple major versions and minor versions.
        self.agreement_version_1_0 = AgreementVersion.objects.create(
            major_version=1,
            minor_version=0,
        )
        self.agreement_version_1_1 = AgreementVersion.objects.create(
            major_version=1,
            minor_version=1,
        )
        self.agreement_version_1_2 = AgreementVersion.objects.create(
            major_version=1,
            minor_version=2,
        )
        self.agreement_version_2_1 = AgreementVersion.objects.create(
            major_version=2,
            minor_version=1,
        )
        self.agreement_version_2_3 = AgreementVersion.objects.create(
            major_version=2,
            minor_version=3,
        )
        self.agreement_version_3_0 = AgreementVersion.objects.create(
            major_version=3,
            minor_version=0,
        )
        self.agreement_version_5_6 = AgreementVersion.objects.create(
            major_version=5,
            minor_version=6,
        )

    def test_agreementmajorversion_model_correctly_populated(self):
        """AgreementMajorVersion is correctly populated."""
        AgreementMajorVersion = self.new_state.apps.get_model("cdsa", "AgreementMajorVersion")
        self.assertEqual(AgreementMajorVersion.objects.count(), 4)
        major_version = AgreementMajorVersion.objects.get(version=1)
        major_version.full_clean()
        major_version = AgreementMajorVersion.objects.get(version=2)
        major_version.full_clean()
        major_version = AgreementMajorVersion.objects.get(version=3)
        major_version.full_clean()
        major_version = AgreementMajorVersion.objects.get(version=5)
        major_version.full_clean()

    def test_agreement_version_major_version_fk_correctly_populated(self):
        """AgreementVersion.major_version_fk is correctly populated."""
        AgreementMajorVersion = self.new_state.apps.get_model("cdsa", "AgreementMajorVersion")
        AgreementVersion = self.new_state.apps.get_model("cdsa", "AgreementVersion")
        # Major version 1.
        major_version = AgreementMajorVersion.objects.get(version=1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_0.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 0)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_1.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_2.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 2)
        # Major version 2.
        major_version = AgreementMajorVersion.objects.get(version=2)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_2_1.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_2_3.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 3)
        # Major version 3.
        major_version = AgreementMajorVersion.objects.get(version=3)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_3_0.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 0)
        # Major version 5.
        major_version = AgreementMajorVersion.objects.get(version=5)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_5_6.pk)
        self.assertEqual(agreement_version.major_version_fk, major_version)
        self.assertEqual(agreement_version.minor_version, 6)
