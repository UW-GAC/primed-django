"""Tests for the `cdsa` app."""

from anvil_consortium_manager.tests.factories import WorkspaceFactory
from django.test import TestCase

from primed.duo.models import DataUseModifier
from primed.duo.tests.factories import DataUseModifierFactory, DataUsePermissionFactory
from primed.primed_anvil.tests.factories import (
    AvailableDataFactory,
    StudyFactory,
    StudySiteFactory,
)
from primed.users.tests.factories import UserFactory

from .. import forms, models
from . import factories


class SignedAgreementFormTest(TestCase):
    """Tests for the SignedAgreementForm class."""

    form_class = forms.SignedAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.representative = UserFactory.create()
        self.agreement_version = factories.AgreementVersionFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_accessors(self):
        """Form is valid when accessors are specified."""
        accessors = UserFactory.create_batch(2)
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
            "accessors": accessors,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_representative(self):
        """Form is invalid when missing representative."""
        form_data = {
            "cc_id": 1234,
            # "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative", form.errors)
        self.assertEqual(len(form.errors["representative"]), 1)
        self.assertIn("required", form.errors["representative"][0])

    def test_missing_cc_id(self):
        """Form is invalid when missing representative."""
        form_data = {
            # "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("required", form.errors["cc_id"][0])

    def test_missing_representative_role(self):
        """Form is invalid when missing representative_role."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            # "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("representative_role", form.errors)
        self.assertEqual(len(form.errors["representative_role"]), 1)
        self.assertIn("required", form.errors["representative_role"][0])

    def test_missing_signing_institution(self):
        """Form is invalid when missing signing_institution."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            # "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signing_institution", form.errors)
        self.assertEqual(len(form.errors["signing_institution"]), 1)
        self.assertIn("required", form.errors["signing_institution"][0])

    def test_missing_version(self):
        """Form is invalid when missing representative_role."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            # "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("required", form.errors["version"][0])

    def test_missing_date_signed(self):
        """Form is invalid when missing representative_role."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            # "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("date_signed", form.errors)
        self.assertEqual(len(form.errors["date_signed"]), 1)
        self.assertIn("required", form.errors["date_signed"][0])

    def test_invalid_cc_id_zero(self):
        """Form is invalid when cc_id is zero."""
        form_data = {
            "cc_id": 0,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("greater than", form.errors["cc_id"][0])

    def test_invalid_duplicate_object(self):
        """Form is invalid with a duplicated object."""
        obj = factories.SignedAgreementFactory.create()
        form_data = {
            "cc_id": obj.cc_id,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("already exists", form.errors["cc_id"][0])

    def test_invalid_version(self):
        """Cannot select an AgreementVersion that is not valid."""
        self.agreement_version.major_version.is_valid = False
        self.agreement_version.major_version.save()
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("version", form.errors)
        self.assertEqual(len(form.errors["version"]), 1)
        self.assertIn("valid choice", form.errors["version"][0])


class SignedAgreementStatusFormTest(TestCase):
    """Tests for the SignedAgreementStatusForm class."""

    form_class = forms.SignedAgreementStatusForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.representative = UserFactory.create()
        self.agreement_version = factories.AgreementVersionFactory.create()
        self.signed_agreement = factories.SignedAgreementFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "status": models.SignedAgreement.StatusChoices.ACTIVE,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_status(self):
        """Form is invalid when missing status."""
        form_data = {}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("status", form.errors)
        self.assertEqual(len(form.errors["status"]), 1)
        self.assertIn("required", form.errors["status"][0])

    def test_invalid_status(self):
        """Cannot select a status that doesn't exist."""
        self.agreement_version.major_version.is_valid = False
        self.agreement_version.major_version.save()
        form_data = {"status": "foo"}
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("status", form.errors)
        self.assertEqual(len(form.errors["status"]), 1)
        self.assertIn("valid choice", form.errors["status"][0])


class SignedAgreementAccessorsFormTest(TestCase):
    """Tests for the SignedAgreementAccessorsForm class."""

    form_class = forms.SignedAgreementAccessorsForm

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "accessors": [],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_one_accessor(self):
        """Form is valid with one accessor."""
        accessor = UserFactory.create()
        form_data = {
            "accessors": [accessor],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_accessors(self):
        """Form is valid with two accessors."""
        accessors = UserFactory.create_batch(2)
        form_data = {
            "accessors": accessors,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_accessor_wrong_class(self):
        """Form is invalid when an object is not a User."""
        form_data = {
            "accessors": [999],
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("accessors", form.errors)
        self.assertEqual(len(form.errors["accessors"]), 1)
        self.assertIn("valid choice", form.errors["accessors"][0])


class MemberAgreementFormTest(TestCase):
    """Tests for the MemberAgreementForm class."""

    form_class = forms.MemberAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        self.study_site = StudySiteFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_signed_agreement(self):
        """Form is invalid when missing signed_agreement."""
        form_data = {
            # "signed_agreement": self.signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("required", form.errors["signed_agreement"][0])

    def test_missing_is_primary(self):
        """Form is invalid when missing study_site."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            # "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_missing_study_site(self):
        """Form is invalid when missing study_site."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "is_primary": True,
            # "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study_site", form.errors)
        self.assertEqual(len(form.errors["study_site"]), 1)
        self.assertIn("required", form.errors["study_site"][0])

    def test_invalid_signed_agreement_already_has_member_agreement(self):
        """Form is invalid with a duplicated object."""
        obj = factories.MemberAgreementFactory.create()
        form_data = {
            "signed_agreement": obj.signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("already exists", form.errors["signed_agreement"][0])

    def test_invalid_signed_agreement_wrong_type(self):
        """Form is invalid when the signed_agreement has the wrong type."""
        obj = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        form_data = {
            "signed_agreement": obj,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])

    def test_invalid_representative_inactive(self):
        """Form is invalid when the representative is not an active user."""
        representative = UserFactory.create(is_active=False)

        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER, representative=representative
        )

        form_data = {
            "signed_agreement": signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("__all__", form.errors)
        self.assertIn("must be an active user", form.errors["__all__"][0])

    def test_invalid_study_site_not_in_representative_study_sites(self):
        """Form is invalid when study_site is not one of representative's study_sites."""
        representative_study_site = StudySiteFactory.create()
        representative = UserFactory.create()
        representative.study_sites.add(representative_study_site)

        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER,
            representative=representative,
        )
        form_data = {
            "signed_agreement": signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertEqual(len(form.errors["__all__"]), 1)
        self.assertIn("study site", form.errors["__all__"][0])

    def test_valid_study_site_in_representative_study_sites(self):
        """Form is valid when study_site matches representative's study_site."""
        representative = UserFactory.create()
        representative.study_sites.add(self.study_site)

        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER,
            representative=representative,
        )
        form_data = {
            "signed_agreement": signed_agreement,
            "is_primary": True,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_representative_has_two_study_sites(self):
        """Form is valid when study_site is one of representative's two study sites."""
        study_site_1 = StudySiteFactory.create()
        study_site_2 = StudySiteFactory.create()

        representative = UserFactory.create()
        representative.study_sites.add(study_site_1, study_site_2)

        signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER,
            representative=representative,
        )
        form_data = {
            "signed_agreement": signed_agreement,
            "is_primary": True,
            "study_site": study_site_1,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())


class DataAffiliateAgreementFormTest(TestCase):
    """Tests for the DataAffiliateAgreementForm class."""

    form_class = forms.DataAffiliateAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)
        self.study = StudyFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "is_primary": True,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_uploaders(self):
        """Form is valid when uploaders are specified."""
        uploaders = UserFactory.create_batch(2)
        form_data = {
            "signed_agreement": self.signed_agreement,
            "is_primary": True,
            "study": self.study,
            "uploaders": uploaders,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_signed_agreement(self):
        """Form is invalid when missing signed_agreement."""
        form_data = {
            # "signed_agreement": self.signed_agreement,
            "is_primary": True,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("required", form.errors["signed_agreement"][0])

    def test_missing_is_primary(self):
        """Form is invalid when missing study_site."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            # "is_primary": True,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_missing_study(self):
        """Form is invalid when missing study."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "is_primary": True,
            # "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study", form.errors)
        self.assertEqual(len(form.errors["study"]), 1)
        self.assertIn("required", form.errors["study"][0])

    def test_invalid_signed_agreement_already_has_agreement_type(self):
        """Form is invalid with a duplicated object."""
        obj = factories.DataAffiliateAgreementFactory.create()
        form_data = {
            "signed_agreement": obj.signed_agreement,
            "is_primary": True,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("already exists", form.errors["signed_agreement"][0])

    def test_invalid_signed_agreement_wrong_type(self):
        """Form is invalid when the signed_agreement has the wrong type."""
        obj = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        form_data = {
            "signed_agreement": obj,
            "is_primary": True,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])

    def test_valid_primary_with_additional_limitations(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study": self.study,
            "is_primary": True,
            "additional_limitations": "test limitations",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_component_with_additional_limitations(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study": self.study,
            "is_primary": False,
            "additional_limitations": "test limitations",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("additional_limitations", form.errors)
        self.assertEqual(len(form.errors["additional_limitations"]), 1)
        self.assertIn("only allowed for primary", form.errors["additional_limitations"][0])

    def test_valid_primary_with_requires_study_review_true(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study": self.study,
            "is_primary": True,
            "requires_study_review": True,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_component_with_requires_study_review_true(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study": self.study,
            "is_primary": False,
            "requires_study_review": True,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("requires_study_review", form.errors)
        self.assertEqual(len(form.errors["requires_study_review"]), 1)
        self.assertIn("can only be True for primary", form.errors["requires_study_review"][0])


class DataAffiliateAgreementUploadersFormTest(TestCase):
    """Tests for the DataAffiliateAgreementUploadersForm class."""

    form_class = forms.DataAffiliateAgreementUploadersForm

    def setUp(self):
        self.signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.DATA_AFFILIATE)

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "uploaders": [],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_one_accessor(self):
        """Form is valid with one accessor."""
        uploader = UserFactory.create()
        form_data = {
            "uploaders": [uploader],
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_accessors(self):
        """Form is valid with two accessors."""
        uploaders = UserFactory.create_batch(2)
        form_data = {
            "uploaders": uploaders,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_uploaders_wrong_class(self):
        """Form is invalid when an object is not a User."""
        form_data = {
            "uploaders": [999],
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("uploaders", form.errors)
        self.assertEqual(len(form.errors["uploaders"]), 1)
        self.assertIn("valid choice", form.errors["uploaders"][0])


class NonDataAffiliateAgreementFormTest(TestCase):
    """Tests for the NonDataAffiliateAgreementForm class."""

    form_class = forms.NonDataAffiliateAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(type=models.SignedAgreement.NON_DATA_AFFILIATE)

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_signed_agreement(self):
        """Form is invalid when missing signed_agreement."""
        form_data = {
            # "signed_agreement": self.signed_agreement,
            "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("required", form.errors["signed_agreement"][0])

    def test_missing_affiliation(self):
        """Form is invalid when missing study."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            # "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("affiliation", form.errors)
        self.assertEqual(len(form.errors["affiliation"]), 1)
        self.assertIn("required", form.errors["affiliation"][0])

    def test_invalid_signed_agreement_already_has_agreement_type(self):
        """Form is invalid with a duplicated object."""
        obj = factories.NonDataAffiliateAgreementFactory.create()
        form_data = {
            "signed_agreement": obj.signed_agreement,
            "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("already exists", form.errors["signed_agreement"][0])

    def test_invalid_signed_agreement_wrong_type(self):
        """Form is invalid when the signed_agreement has the wrong type."""
        obj = factories.SignedAgreementFactory.create(type=models.SignedAgreement.MEMBER)
        form_data = {
            "signed_agreement": obj,
            "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])


class CDSAWorkspaceFormTest(TestCase):
    """Tests for the CDSAWorkspaceForm class."""

    form_class = forms.CDSAWorkspaceForm

    def setUp(self):
        """Create a workspace for use in the form."""
        self.workspace = WorkspaceFactory()
        self.study = StudyFactory.create()
        self.requester = UserFactory.create()
        self.duo_permission = DataUsePermissionFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_one_data_use_modifier(self):
        DataUseModifierFactory.create()
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "data_use_modifier": DataUseModifier.objects.all(),
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_with_two_data_use_modifiers(self):
        DataUseModifierFactory.create_batch(2)
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "data_use_modifier": DataUseModifier.objects.all(),
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_workspace(self):
        """Form is invalid when missing workspace."""
        form_data = {
            # "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("required", form.errors["workspace"][0])

    def test_invalid_missing_study(self):
        """Form is invalid when missing study."""
        form_data = {
            "workspace": self.workspace,
            # "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("study", form.errors)
        self.assertEqual(len(form.errors["study"]), 1)
        self.assertIn("required", form.errors["study"][0])

    def test_invalid_missing_requested_by(self):
        """Form is invalid when missing requested_by."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            # "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("requested_by", form.errors)
        self.assertEqual(len(form.errors["requested_by"]), 1)
        self.assertIn("required", form.errors["requested_by"][0])

    def test_invalid_missing_data_use_permission(self):
        """Form is invalid when missing data_use_permission."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            # "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("data_use_permission", form.errors)
        self.assertEqual(len(form.errors["data_use_permission"]), 1)
        self.assertIn("required", form.errors["data_use_permission"][0])

    def test_valid_additional_limitations(self):
        """Form is invalid when missing data_use_limitations."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "additional_limitations": "test limitations",
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.instance.additional_limitations, "test limitations")

    def test_invalid_missing_acknowledgments(self):
        """Form is invalid when missing acknowledgments."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            # "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("acknowledgments", form.errors)
        self.assertEqual(len(form.errors["acknowledgments"]), 1)
        self.assertIn("required", form.errors["acknowledgments"][0])

    def test_invalid_missing_gsr_restricted(self):
        """Form is valid? when missing gsr_restricted."""
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            # "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("gsr_restricted", form.errors)
        self.assertEqual(len(form.errors["gsr_restricted"]), 1)
        self.assertIn("required", form.errors["gsr_restricted"][0])

    def test_invalid_duplicate_workspace(self):
        """Form is invalid with a duplicated workspace."""
        cdsa_workspace = factories.CDSAWorkspaceFactory.create()
        form_data = {
            "workspace": cdsa_workspace.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("workspace", form.errors)
        self.assertEqual(len(form.errors["workspace"]), 1)
        self.assertIn("already exists", form.errors["workspace"][0])

    def test_valid_one_available_data(self):
        """Form is valid with necessary input and one available data record."""
        available_data = AvailableDataFactory.create()
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "available_data": [available_data],
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_two_available_data(self):
        """Form is valid with necessary input and two available data records."""
        available_data = AvailableDataFactory.create_batch(2)
        form_data = {
            "workspace": self.workspace,
            "study": self.study,
            "requested_by": self.requester,
            "data_use_permission": self.duo_permission,
            "acknowledgments": "test acknowledgmnts",
            "available_data": available_data,
            "gsr_restricted": False,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())
