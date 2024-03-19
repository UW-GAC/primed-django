"""Tests for the tables in the `cdsa` app."""

from anvil_consortium_manager.models import GroupAccountMembership, Workspace
from anvil_consortium_manager.tests.factories import (
    GroupAccountMembershipFactory,
    WorkspaceGroupSharingFactory,
)
from django.test import TestCase

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
from primed.users.tests.factories import UserFactory

from .. import models, tables
from . import factories


class AgreementVersionTableTest(TestCase):
    model = models.AgreementVersion
    model_factory = factories.AgreementVersionFactory
    table_class = tables.AgreementVersionTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)


class SignedAgreementTableTest(TestCase):
    model = models.SignedAgreement
    table_class = tables.SignedAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        factories.MemberAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        factories.MemberAgreementFactory.create()
        obj = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)

    def test_ordering(self):
        """Instances are ordered alphabetically by cc_id."""
        instance_1 = factories.MemberAgreementFactory.create(signed_agreement__cc_id=2)
        instance_2 = factories.MemberAgreementFactory.create(signed_agreement__cc_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2.signed_agreement)
        self.assertEqual(table.data[1], instance_1.signed_agreement)


class MemberAgreementTableTest(TestCase):
    model = models.MemberAgreement
    model_factory = factories.MemberAgreementFactory
    table_class = tables.MemberAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)

    def test_ordering(self):
        """Instances are ordered alphabetically by cc_id."""
        instance_1 = self.model_factory.create(signed_agreement__cc_id=2)
        instance_2 = self.model_factory.create(signed_agreement__cc_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class DataAffiliateAgreementTableTest(TestCase):
    model = models.DataAffiliateAgreement
    model_factory = factories.DataAffiliateAgreementFactory
    table_class = tables.DataAffiliateAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)

    def test_ordering(self):
        """Instances are ordered alphabetically by cc_id."""
        instance_1 = self.model_factory.create(signed_agreement__cc_id=2)
        instance_2 = self.model_factory.create(signed_agreement__cc_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class NonDataAffiliateAgreementTableTest(TestCase):
    model = models.NonDataAffiliateAgreement
    model_factory = factories.NonDataAffiliateAgreementFactory
    table_class = tables.NonDataAffiliateAgreementTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_number_accessors(self):
        """Table shows correct count for number of accessors."""
        self.model_factory.create()
        obj = self.model_factory.create()
        GroupAccountMembershipFactory.create(
            group=obj.signed_agreement.anvil_access_group
        )
        obj_2 = self.model_factory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group=obj_2.signed_agreement.anvil_access_group
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.rows[0].get_cell("number_accessors"), 0)
        self.assertEqual(table.rows[1].get_cell("number_accessors"), 1)
        self.assertEqual(table.rows[2].get_cell("number_accessors"), 2)

    def test_ordering(self):
        """Instances are ordered alphabetically by cc_id."""
        instance_1 = self.model_factory.create(signed_agreement__cc_id=2)
        instance_2 = self.model_factory.create(signed_agreement__cc_id=1)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class RepresentativeRecordsTableTest(TestCase):
    """Tests for the RepresentativeRecordsTable class."""

    model = models.SignedAgreement
    table_class = tables.RepresentativeRecordsTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        factories.MemberAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        factories.MemberAgreementFactory.create()
        factories.DataAffiliateAgreementFactory.create()
        factories.NonDataAffiliateAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_render_signing_group(self):
        table = self.table_class(self.model.objects.all())
        # Members.
        study_site = StudySiteFactory.create(short_name="Test Site")
        record = factories.MemberAgreementFactory(study_site=study_site)
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Site"
        )
        # Data affiliates.
        study = StudyFactory.create(short_name="Test Study")
        record = factories.DataAffiliateAgreementFactory(study=study)
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Study"
        )
        # Non-data affiliates.
        record = factories.NonDataAffiliateAgreementFactory(affiliation="Test Affil")
        self.assertEqual(
            table.render_signing_group(record.signed_agreement), "Test Affil"
        )
        # Other catch-all case that shouldn't happen.
        record = factories.SignedAgreementFactory()
        self.assertIsNone(table.render_signing_group(record))

    def test_ordering(self):
        """Instances are ordered alphabetically by representative name."""
        instance_1 = factories.MemberAgreementFactory.create(
            signed_agreement__representative__name="zzz"
        )
        instance_2 = factories.MemberAgreementFactory.create(
            signed_agreement__representative__name="aaa"
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2.signed_agreement)
        self.assertEqual(table.data[1], instance_1.signed_agreement)


class StudyRecordsTableTest(TestCase):
    """Tests for the StudyRecordsTable class."""

    model = models.DataAffiliateAgreement
    model_factory = factories.DataAffiliateAgreementFactory
    table_class = tables.StudyRecordsTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_two_objects(self):
        self.model_factory.create_batch(2)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)

    def test_ordering(self):
        """Instances are ordered alphabetically by study short name."""
        instance_1 = self.model_factory.create(study__short_name="zzz")
        instance_2 = self.model_factory.create(study__short_name="aaa")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class UserAccessRecordsTableTest(TestCase):
    """Tests for the UserAccessRecordsTable class."""

    model = GroupAccountMembership
    table_class = tables.UserAccessRecordsTable

    def test_row_count_with_no_objects(self):
        factories.MemberAgreementFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_agreement(self):
        member_agreement = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create(
            group__signedagreement=member_agreement.signed_agreement
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_one_agreement_multiple_members(self):
        member_agreement = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create_batch(
            5, group__signedagreement=member_agreement.signed_agreement
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 5)

    def test_row_count_with_two_agreements_multiple_members(self):
        member_agreement_1 = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create_batch(
            2, group__signedagreement=member_agreement_1.signed_agreement
        )
        member_agreement_2 = factories.MemberAgreementFactory.create()
        GroupAccountMembershipFactory.create_batch(
            3, group__signedagreement=member_agreement_2.signed_agreement
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 5)

    def test_includes_components(self):
        agreement_1 = factories.MemberAgreementFactory.create(is_primary=True)
        GroupAccountMembershipFactory.create(
            group__signedagreement=agreement_1.signed_agreement
        )
        agreement_2 = factories.MemberAgreementFactory.create(is_primary=False)
        GroupAccountMembershipFactory.create(
            group__signedagreement=agreement_2.signed_agreement
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)

    def test_render_signing_group(self):
        table = self.table_class(self.model.objects.all())
        # Members.
        agreement = factories.MemberAgreementFactory(study_site__short_name="Test Site")
        record = GroupAccountMembershipFactory.create(
            group__signedagreement=agreement.signed_agreement
        )
        self.assertEqual(table.render_signing_group(record), "Test Site")
        # Data affiliates.
        agreement = factories.DataAffiliateAgreementFactory(
            study__short_name="Test Study"
        )
        record = GroupAccountMembershipFactory.create(
            group__signedagreement=agreement.signed_agreement
        )
        self.assertEqual(table.render_signing_group(record), "Test Study")
        # Non-data affiliates.
        agreement = factories.NonDataAffiliateAgreementFactory(affiliation="Test affil")
        record = GroupAccountMembershipFactory.create(
            group__signedagreement=agreement.signed_agreement
        )
        self.assertEqual(table.render_signing_group(record), "Test affil")
        # Other catch-all case that shouldn't happen.
        agreement = factories.SignedAgreementFactory()
        record = GroupAccountMembershipFactory.create(group__signedagreement=agreement)
        self.assertIsNone(table.render_signing_group(record))

    def test_ordering(self):
        """Instances are ordered alphabetically by user name."""
        agreement = factories.MemberAgreementFactory.create()
        user_1 = UserFactory.create(name="zzz")
        instance_1 = GroupAccountMembershipFactory.create(
            group__signedagreement=agreement.signed_agreement,
            account__user=user_1,
        )
        user_2 = UserFactory.create(name="aaa")
        instance_2 = GroupAccountMembershipFactory.create(
            group__signedagreement=agreement.signed_agreement,
            account__user=user_2,
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class CDSAWorkspaceRecordsTableTest(TestCase):
    """Tests for the CDSAWorkspaceRecordsTable class."""

    model = models.CDSAWorkspace
    table_class = tables.CDSAWorkspaceRecordsTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)
        self.assertIn(cdsa_workspace, table.data)

    def test_row_count_with_two_objects(self):
        cdsa_workspaces = factories.CDSAWorkspaceFactory.create_batch(2)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 2)
        self.assertIn(cdsa_workspaces[0], table.data)
        self.assertIn(cdsa_workspaces[1], table.data)

    def test_render_date_shared(self):
        table = self.table_class(self.model.objects.all())
        # Not shared.
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        self.assertEqual(table.render_date_shared(cdsa_workspace), "—")
        # Shared.
        WorkspaceGroupSharingFactory.create(
            workspace=cdsa_workspace.workspace, group__name="PRIMED_ALL"
        )
        self.assertNotEqual(table.render_date_shared(cdsa_workspace), "—")

    def test_ordering(self):
        """Instances are ordered alphabetically by user name."""
        agreement = factories.DataAffiliateAgreementFactory.create()
        instance_1 = factories.CDSAWorkspaceFactory.create(
            study=agreement.study, workspace__name="zzz"
        )
        instance_2 = factories.CDSAWorkspaceFactory.create(
            study=agreement.study, workspace__name="aaa"
        )
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2)
        self.assertEqual(table.data[1], instance_1)


class CDSAWorkspaceStaffTableTest(TestCase):
    """Tests for the CDSAWorkspaceStaffTable class."""

    model = Workspace
    model_factory = factories.CDSAWorkspaceFactory
    table_class = tables.CDSAWorkspaceStaffTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_ordering(self):
        """Instances are ordered alphabetically by user name."""
        instance_1 = factories.CDSAWorkspaceFactory.create(workspace__name="zzz")
        instance_2 = factories.CDSAWorkspaceFactory.create(workspace__name="aaa")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2.workspace)
        self.assertEqual(table.data[1], instance_1.workspace)


class CDSAWorkspaceUserTableTest(TestCase):
    """Tests for the CDSAWorkspaceUserTable class."""

    model = Workspace
    model_factory = factories.CDSAWorkspaceFactory
    table_class = tables.CDSAWorkspaceUserTable

    def test_row_count_with_no_objects(self):
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 0)

    def test_row_count_with_one_object(self):
        self.model_factory.create()
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 1)

    def test_row_count_with_three_objects(self):
        self.model_factory.create_batch(3)
        table = self.table_class(self.model.objects.all())
        self.assertEqual(len(table.rows), 3)

    def test_ordering(self):
        """Instances are ordered alphabetically by user name."""
        instance_1 = factories.CDSAWorkspaceFactory.create(workspace__name="zzz")
        instance_2 = factories.CDSAWorkspaceFactory.create(workspace__name="aaa")
        table = self.table_class(self.model.objects.all())
        self.assertEqual(table.data[0], instance_2.workspace)
        self.assertEqual(table.data[1], instance_1.workspace)
