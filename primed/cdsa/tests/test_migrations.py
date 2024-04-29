"""Tests for data migrations in the app."""

from django_test_migrations.contrib.unittest_case import MigratorTestCase



class AgreementMajorVersionMigrationsTest(MigratorTestCase):
    """Tests for the migrations associated with creating the new AgreementMajorVersion model."""

    migrate_from = ("cdsa", "0001_initial")
    migrate_to = ("cdsa", "0007_alter_agreementversion_major_version")

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

    def test_agreement_version_major_version_correctly_populated(self):
        """AgreementVersion.major_version is correctly populated."""
        AgreementMajorVersion = self.new_state.apps.get_model("cdsa", "AgreementMajorVersion")
        AgreementVersion = self.new_state.apps.get_model("cdsa", "AgreementVersion")
        # Major version 1.
        major_version = AgreementMajorVersion.objects.get(version=1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_0.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 0)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_1.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_1_2.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 2)
        # Major version 2.
        major_version = AgreementMajorVersion.objects.get(version=2)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_2_1.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 1)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_2_3.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 3)
        # Major version 3.
        major_version = AgreementMajorVersion.objects.get(version=3)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_3_0.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 0)
        # Major version 5.
        major_version = AgreementMajorVersion.objects.get(version=5)
        agreement_version = AgreementVersion.objects.get(pk=self.agreement_version_5_6.pk)
        agreement_version.full_clean()
        self.assertEqual(agreement_version.major_version, major_version)
        self.assertEqual(agreement_version.minor_version, 6)


class PopulateIsPrimaryMigrationsForwardTest(MigratorTestCase):
    """Tests for the migrations associated with creating the new AgreementMajorVersion model."""

    migrate_from = ("cdsa", "0018_dataaffiliateagreement_requires_study_review_and_more")
    migrate_to = ("cdsa", "0022_remove_signedagreement_is_primary")

    def prepare(self):
        """Prepare some data before the migration."""
        # Get model definition for the old state.
        User = self.old_state.apps.get_model("users", "User")
        ManagedGroup = self.old_state.apps.get_model("anvil_consortium_manager", "ManagedGroup")
        StudySite = self.old_state.apps.get_model("primed_anvil", "StudySite")
        Study = self.old_state.apps.get_model("primed_anvil", "Study")
        AgreementMajorVersion = self.old_state.apps.get_model("cdsa", "AgreementMajorVersion")
        AgreementVersion = self.old_state.apps.get_model("cdsa", "AgreementVersion")
        SignedAgreement = self.old_state.apps.get_model("cdsa", "SignedAgreement")
        MemberAgreement = self.old_state.apps.get_model("cdsa", "MemberAgreement")
        DataAffiliateAgreement = self.old_state.apps.get_model("cdsa", "DataAffiliateAgreement")
        NonDataAffiliateAgreement = self.old_state.apps.get_model("cdsa", "NonDataAffiliateAgreement")
        # Populate some signed agreements.
        agreement_version = AgreementVersion.objects.create(
            major_version=AgreementMajorVersion.objects.create(version=1, is_valid=True),
            minor_version=0,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=1,
            representative=User.objects.create_user(username="test1", password="test1"),
            representative_role="Test role 1",
            signing_institution="Test institution 1",
            type="member",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess1", email="testaccess1@example.com"),
            is_primary=True
        )
        self.member_agreement_1 = MemberAgreement.objects.create(
            signed_agreement=tmp,
            study_site=StudySite.objects.create(short_name="test1", full_name="Test Study 1"),
        )
        tmp = SignedAgreement.objects.create(
            cc_id=2,
            representative=User.objects.create_user(username="test2", password="test2"),
            representative_role="Test role 2",
            signing_institution="Test institution 2",
            type="member",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess2", email="testaccess2@example.com"),
            is_primary=False
        )
        self.member_agreement_2 = MemberAgreement.objects.create(
            signed_agreement=tmp,
            study_site=StudySite.objects.get(short_name="test1"),
        )
        tmp = SignedAgreement.objects.create(
            cc_id=3,
            representative=User.objects.create_user(username="test3", password="test3"),
            representative_role="Test role 3",
            signing_institution="Test institution 3",
            type="data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess3", email="testaccess3@example.com"),
            is_primary=True
        )
        self.data_affiliate_agreement_1 = DataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
            study=Study.objects.create(short_name="test2", full_name="Test Study Site 2"),
            anvil_upload_group=ManagedGroup.objects.create(name="testupload1", email="testupload1@example.com"),
        )
        tmp = SignedAgreement.objects.create(
            cc_id=4,
            representative=User.objects.create_user(username="test4", password="test4"),
            representative_role="Test role 4",
            signing_institution="Test institution 4",
            type="data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess4", email="testaccess4@example.com"),
            is_primary=False
        )
        self.data_affiliate_agreement_2 = DataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
            study=Study.objects.get(short_name="test2"),
            anvil_upload_group=ManagedGroup.objects.create(name="testupload2", email="testupload2@example.com"),
        )
        tmp = SignedAgreement.objects.create(
            cc_id=5,
            representative=User.objects.create_user(username="test5", password="test5"),
            representative_role="Test role 5",
            signing_institution="Test institution 5",
            type="non_data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess5", email="testaccess5@example.com"),
            is_primary=False
        )
        self.non_data_affiliate_agreement = NonDataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
        )

    def test_is_primary_correctly_populated(self):
#        import ipdb; ipdb.set_trace()
        MemberAgreement = self.new_state.apps.get_model("cdsa", "MemberAgreement")
        DataAffiliateAgreement = self.new_state.apps.get_model("cdsa", "DataAffiliateAgreement")
        NonDataAffiliateAgreement = self.new_state.apps.get_model("cdsa", "NonDataAffiliateAgreement")
        instance = MemberAgreement.objects.get(pk=self.member_agreement_1.pk)
        self.assertEqual(instance.is_primary, True)
        instance = MemberAgreement.objects.get(pk=self.member_agreement_2.pk)
        self.assertEqual(instance.is_primary, False)
        instance = DataAffiliateAgreement.objects.get(pk=self.data_affiliate_agreement_1.pk)
        self.assertEqual(instance.is_primary, True)
        instance = DataAffiliateAgreement.objects.get(pk=self.data_affiliate_agreement_2.pk)
        self.assertEqual(instance.is_primary, False)
        instance = NonDataAffiliateAgreement.objects.get(pk=self.non_data_affiliate_agreement.pk)
        self.assertFalse(hasattr(self.non_data_affiliate_agreement, "is_primary"))


class PopulateIsPrimaryMigrationsBackwardTest(MigratorTestCase):
    """Tests for the migrations associated with creating the new AgreementMajorVersion model."""

    migrate_from = ("cdsa", "0022_remove_signedagreement_is_primary")
    migrate_to = ("cdsa", "0018_dataaffiliateagreement_requires_study_review_and_more")

    def prepare(self):
        """Prepare some data before the migration."""
        # Get model definition for the old state.
        User = self.old_state.apps.get_model("users", "User")
        ManagedGroup = self.old_state.apps.get_model("anvil_consortium_manager", "ManagedGroup")
        StudySite = self.old_state.apps.get_model("primed_anvil", "StudySite")
        Study = self.old_state.apps.get_model("primed_anvil", "Study")
        AgreementMajorVersion = self.old_state.apps.get_model("cdsa", "AgreementMajorVersion")
        AgreementVersion = self.old_state.apps.get_model("cdsa", "AgreementVersion")
        SignedAgreement = self.old_state.apps.get_model("cdsa", "SignedAgreement")
        MemberAgreement = self.old_state.apps.get_model("cdsa", "MemberAgreement")
        DataAffiliateAgreement = self.old_state.apps.get_model("cdsa", "DataAffiliateAgreement")
        NonDataAffiliateAgreement = self.old_state.apps.get_model("cdsa", "NonDataAffiliateAgreement")
        # Populate some signed agreements.
        agreement_version = AgreementVersion.objects.create(
            major_version=AgreementMajorVersion.objects.create(version=1, is_valid=True),
            minor_version=0,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=1,
            representative=User.objects.create_user(username="test1", password="test1"),
            representative_role="Test role 1",
            signing_institution="Test institution 1",
            type="member",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess1", email="testaccess1@example.com"),
        )
        self.member_agreement_1 = MemberAgreement.objects.create(
            signed_agreement=tmp,
            study_site=StudySite.objects.create(short_name="test1", full_name="Test Study 1"),
            is_primary=True,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=2,
            representative=User.objects.create_user(username="test2", password="test2"),
            representative_role="Test role 2",
            signing_institution="Test institution 2",
            type="member",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess2", email="testaccess2@example.com"),
        )
        self.member_agreement_2 = MemberAgreement.objects.create(
            signed_agreement=tmp,
            study_site=StudySite.objects.get(short_name="test1"),
            is_primary=False,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=3,
            representative=User.objects.create_user(username="test3", password="test3"),
            representative_role="Test role 3",
            signing_institution="Test institution 3",
            type="data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess3", email="testaccess3@example.com"),
        )
        self.data_affiliate_agreement_1 = DataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
            study=Study.objects.create(short_name="test2", full_name="Test Study Site 2"),
            anvil_upload_group=ManagedGroup.objects.create(name="testupload1", email="testupload1@example.com"),
            is_primary=True,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=4,
            representative=User.objects.create_user(username="test4", password="test4"),
            representative_role="Test role 4",
            signing_institution="Test institution 4",
            type="data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess4", email="testaccess4@example.com"),
        )
        self.data_affiliate_agreement_2 = DataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
            study=Study.objects.get(short_name="test2"),
            anvil_upload_group=ManagedGroup.objects.create(name="testupload2", email="testupload2@example.com"),
            is_primary=False,
        )
        tmp = SignedAgreement.objects.create(
            cc_id=5,
            representative=User.objects.create_user(username="test5", password="test5"),
            representative_role="Test role 5",
            signing_institution="Test institution 5",
            type="non_data_affiliate",
            version=agreement_version,
            anvil_access_group=ManagedGroup.objects.create(name="testaccess5", email="testaccess5@example.com"),
        )
        self.non_data_affiliate_agreement = NonDataAffiliateAgreement.objects.create(
            signed_agreement=tmp,
        )

    def test_is_primary_correctly_populated(self):
        SignedAgreement = self.new_state.apps.get_model("cdsa", "SignedAgreement")
        instance = SignedAgreement.objects.get(pk=self.member_agreement_1.signed_agreement.pk)
        self.assertEqual(instance.is_primary, True)
        instance = SignedAgreement.objects.get(pk=self.member_agreement_2.signed_agreement.pk)
        self.assertEqual(instance.is_primary, False)
        instance = SignedAgreement.objects.get(pk=self.data_affiliate_agreement_1.signed_agreement.pk)
        self.assertEqual(instance.is_primary, True)
        instance = SignedAgreement.objects.get(pk=self.data_affiliate_agreement_2.signed_agreement.pk)
        self.assertEqual(instance.is_primary, False)
        instance = SignedAgreement.objects.get(pk=self.non_data_affiliate_agreement.signed_agreement.pk)
        self.assertTrue(instance.is_primary)
