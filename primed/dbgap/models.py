import logging
import re

import jsonschema
import requests
from anvil_consortium_manager.models import BaseWorkspaceData
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from primed.primed_anvil.models import DataUseOntologyModel, Study

from . import constants, managers

logger = logging.getLogger(__name__)


class dbGaPStudyAccession(TimeStampedModel, models.Model):
    """A model to track dbGaP study accessions."""

    # Consider making this many to many since some dbgap acessions contain multiple studies.
    phs = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        unique=True,
        help_text="""The dbGaP study accession integer associated with this workspace (e.g., 7 for phs000007).""",
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        help_text="The study associated with this dbGaP study accession.",
    )
    history = HistoricalRecords()

    # Store a regex for the full accession.
    PHS_REGEX = r"^phs(?P<phs>\d{6})$"
    FULL_ACCESSION_REGEX = (
        r"^phs(?P<phs>\d{6})\.v(?P<version>\d+?)\.p(?P<participant_set>\d+?)$"
    )
    DBGAP_STUDY_URL = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi"

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP study accession"
        verbose_name_plural = " dbGaP study accessions"

    def __str__(self):
        return "phs{phs:06d} - {study}".format(
            phs=self.phs, study=self.study.short_name
        )

    def get_absolute_url(self):
        return reverse("dbgap:dbgap_study_accessions:detail", kwargs={"pk": self.pk})

    def dbgap_get_current_full_accession_numbers(self):
        """Query dbGaP to get the full accession, including version and participant set numbers, for this phs."""
        # This url should will resolve to the most recent version/participant set id.
        response = requests.get(
            self.DBGAP_STUDY_URL,
            params={"study_id": "phs{phs:06d}".format(phs=self.phs)},
            allow_redirects=False,
        )
        full_accession = response.next.url.split("study_id=")[1]
        match = re.match(self.FULL_ACCESSION_REGEX, full_accession)
        d = {
            "phs": int(match.group("phs")),
            "version": int(match.group("version")),
            "participant_set": int(match.group("participant_set")),
        }
        return d


class dbGaPWorkspace(DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track additional data about dbGaP data in a workspace."""

    # PositiveIntegerField allows 0 and we want this to be 1 or higher.
    # We'll need to add a separate constraint.
    dbgap_study_accession = models.ForeignKey(
        dbGaPStudyAccession, on_delete=models.PROTECT
    )

    # Should dbgap_study, version and participant set be their own model -- dbGaPStudyVersion?
    # Note that having this -- wec ould have derived data workspaces linking to multiple dbgap study versions.
    dbgap_version = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP study version associated with this Workspace.""",
    )

    # Do we want version here?
    dbgap_participant_set = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP participant set associated with this Workspace.""",
    )
    dbgap_consent_code = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="The numeric code assigned to this consent group by dbGaP",
    )
    dbgap_consent_abbreviation = models.CharField(
        max_length=63,
        help_text="""The consent abbreviation from dbGaP for this study consent group (e.g., GRU-NPU-MDS).""",
    )
    # This field would ideally be created from the DataUseOntology fields to minimize data duplication.
    # Unfortunately, there are often legacy codes that don't fit into the current main/modifiers model.
    # We also need this field to match to dbGaP authorized access, so store it separately."""

    data_use_limitations = models.TextField(
        help_text="""The full data use limitations for this workspace."""
    )

    history = HistoricalRecords()

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP workspace"
        verbose_name_plural = " dbGaP workspaces"
        constraints = [
            # Model uniqueness.
            models.UniqueConstraint(
                name="unique_dbgap_workspace",
                fields=[
                    "dbgap_study_accession",
                    "dbgap_version",
                    "dbgap_consent_abbreviation",
                ],
            ),
        ]

    def __str__(self):
        """String method.
        Returns:
            A string showing the workspace name of the object.
        """
        return "{} ({} - {})".format(
            self.dbgap_study_accession.study.short_name,
            self.get_dbgap_accession(),
            self.dbgap_consent_abbreviation,
        )

    def get_dbgap_accession(self):
        return "phs{phs:06d}.v{v}.p{ps}".format(
            phs=self.dbgap_study_accession.phs,
            v=self.dbgap_version,
            ps=self.dbgap_participant_set,
        )


class dbGaPApplication(TimeStampedModel, models.Model):
    """A model to track dbGaP applications."""

    principal_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The principal investigator associated with on this dbGaP application.",
    )
    # TODO: change to dbgap_project_id for consistency.
    project_id = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        unique=True,
        help_text="The dbGaP-assigned project_id for this application.",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = " dbGaP application"

    def __str__(self):
        return "{}".format(self.project_id)

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse("dbgap:dbgap_applications:detail", kwargs={"pk": self.pk})

    def create_dars_from_json(self, json):
        """Add DARs for this application from the dbGaP json for this project/application."""
        # Validate the json.
        jsonschema.validate(json, constants.json_dar_schema)
        # Log the json.
        msg = "Creating DARs using json...\n  {json}".format(
            json=json,
        )
        logger.info(msg)
        dars = []
        project_json = json[0]
        # Make sure that the project_id matches.
        project_id = project_json["Project_id"]
        if project_id != self.project_id:
            raise ValueError("project_id does not match this dbGaPApplication.")
        # Loop over studies and requests to create DARs.
        # Do not save them until everything has been successfully created.
        for study_json in project_json["studies"]:
            # Consider making this a model manager method for dbGaPStudyAccession, since it may be common.
            # Get the dbGaPStudyAccession associated with this phs.
            phs = int(
                re.match(
                    dbGaPStudyAccession.PHS_REGEX, study_json["study_accession"]
                ).group("phs")
            )
            study_accession = dbGaPStudyAccession.objects.get(phs=phs)
            # Get the most recent version and participant set number from dbGaP.
            accession_numbers = (
                study_accession.dbgap_get_current_full_accession_numbers()
            )
            # Create the DAR.
            for request_json in study_json["requests"]:
                dar = dbGaPDataAccessRequest(
                    dbgap_dar_id=request_json["DAR"],
                    dbgap_application=self,
                    dbgap_study_accession=study_accession,
                    dbgap_version=accession_numbers["version"],
                    dbgap_participant_set=accession_numbers["participant_set"],
                    dbgap_consent_code=request_json["consent_code"],
                    dbgap_consent_abbreviation=request_json["consent_abbrev"],
                    dbgap_current_status=request_json["current_DAR_status"],
                )
                dar.full_clean()
                dars.append(dar)
        # Create the DARs in bulk - there are usually a lot of them.
        dbGaPDataAccessRequest.objects.bulk_create(dars)
        return dars


class dbGaPDataAccessRequest(TimeStampedModel, models.Model):
    """A model to track dbGaP data access requests."""

    # The value here is what appears in the DAR JSON from dbGaP.
    # So far I am aware of "approved" and "closed".
    APPROVED = "approved"
    CLOSED = "closed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NEW = "new"
    DBGAP_CURRENT_STATUS_CHOICES = (
        (APPROVED, "Approved"),
        (CLOSED, "Closed"),
        (REJECTED, "Rejected"),
        (EXPIRED, "Expired"),
        (NEW, "New"),  # What is the difference between new and approved?
    )

    dbgap_dar_id = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        unique=True,
    )
    dbgap_application = models.ForeignKey(
        dbGaPApplication,
        on_delete=models.PROTECT,
        help_text="The dbGaP application associated with this DAR.",
    )
    dbgap_study_accession = models.ForeignKey(
        dbGaPStudyAccession,
        on_delete=models.PROTECT,
        help_text="The dbGaP study accession associated with this DAR.",
    )
    dbgap_version = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="The version of the dbGaP study accession that this application grants access to.",
    )
    dbgap_participant_set = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="The participant set of the dbGaP study accession that this application grants access to.",
    )
    dbgap_consent_code = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="The numeric code assigned to this consent group by dbGaP",
    )
    dbgap_consent_abbreviation = models.CharField(
        max_length=31, help_text="The abbreviation for this consent group."
    )
    dbgap_current_status = models.CharField(
        max_length=31, choices=DBGAP_CURRENT_STATUS_CHOICES
    )

    history = HistoricalRecords()

    objects = managers.dbGaPDataAccessRequestManager()

    class Meta:
        verbose_name = " dbGaP data access request"

    def __str__(self):
        return "{}".format(self.dbgap_dar_id)
