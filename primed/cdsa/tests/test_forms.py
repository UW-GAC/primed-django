"""Tests for the `cdsa` app."""

from django.test import TestCase

from primed.primed_anvil.tests.factories import StudyFactory, StudySiteFactory
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
            "is_primary": True,
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
            "is_primary": True,
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
            "is_primary": True,
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
            "is_primary": True,
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
            "is_primary": True,
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
            "is_primary": True,
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
            "is_primary": True,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("date_signed", form.errors)
        self.assertEqual(len(form.errors["date_signed"]), 1)
        self.assertIn("required", form.errors["date_signed"][0])

    def test_missing_is_primary(self):
        """Form is invalid when missing representative_role."""
        form_data = {
            "cc_id": 1234,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
            # "is_primary": True,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("is_primary", form.errors)
        self.assertEqual(len(form.errors["is_primary"]), 1)
        self.assertIn("required", form.errors["is_primary"][0])

    def test_invalid_cc_id_zero(self):
        """Form is invalid when cc_id is zero."""
        form_data = {
            "cc_id": 0,
            "representative": self.representative,
            "representative_role": "Test role",
            "signing_institution": "Test insitution",
            "version": self.agreement_version,
            "date_signed": "2023-01-01",
            "is_primary": True,
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
            "is_primary": True,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("cc_id", form.errors)
        self.assertEqual(len(form.errors["cc_id"]), 1)
        self.assertIn("already exists", form.errors["cc_id"][0])


class MemberAgreementFormTest(TestCase):
    """Tests for the MemberAgreementForm class."""

    form_class = forms.MemberAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        self.study_site = StudySiteFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_signed_agreement(self):
        """Form is invalid when missing signed_agreement."""
        form_data = {
            # "signed_agreement": self.signed_agreement,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("required", form.errors["signed_agreement"][0])

    def test_missing_study_site(self):
        """Form is invalid when missing study_site."""
        form_data = {
            "signed_agreement": self.signed_agreement,
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
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("already exists", form.errors["signed_agreement"][0])

    def test_invalid_signed_agreement_wrong_type(self):
        """Form is invalid when the signed_agreement has the wrong type."""
        obj = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        form_data = {
            "signed_agreement": obj,
            "study_site": self.study_site,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])


class DataAffiliateAgreementFormTest(TestCase):
    """Tests for the DataAffiliateAgreementForm class."""

    form_class = forms.DataAffiliateAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.DATA_AFFILIATE
        )
        self.study = StudyFactory.create()

    def test_valid(self):
        """Form is valid with necessary input."""
        form_data = {
            "signed_agreement": self.signed_agreement,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertTrue(form.is_valid())

    def test_missing_signed_agreement(self):
        """Form is invalid when missing signed_agreement."""
        form_data = {
            # "signed_agreement": self.signed_agreement,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("required", form.errors["signed_agreement"][0])

    def test_missing_study(self):
        """Form is invalid when missing study."""
        form_data = {
            "signed_agreement": self.signed_agreement,
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
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("already exists", form.errors["signed_agreement"][0])

    def test_invalid_signed_agreement_wrong_type(self):
        """Form is invalid when the signed_agreement has the wrong type."""
        obj = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        form_data = {
            "signed_agreement": obj,
            "study": self.study,
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])


class NonDataAffiliateAgreementFormTest(TestCase):
    """Tests for the NonDataAffiliateAgreementForm class."""

    form_class = forms.NonDataAffiliateAgreementForm

    def setUp(self):
        """Create related objects for use in the form."""
        self.signed_agreement = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.NON_DATA_AFFILIATE
        )

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
        obj = factories.SignedAgreementFactory.create(
            type=models.SignedAgreement.MEMBER
        )
        form_data = {
            "signed_agreement": obj,
            "affiliation": "Foo Bar",
        }
        form = self.form_class(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("signed_agreement", form.errors)
        self.assertEqual(len(form.errors["signed_agreement"]), 1)
        self.assertIn("expected type", form.errors["signed_agreement"][0])
