"""Model definitions for the `dbgap` app.

Naming conventions:

Fields for information obtained, assigned by dbGaP, or referring to external resources on dbGaP are typically
prefixed with "dbgap". The exception is for ForeignKeys, which use the snake_case name of the model they are
referencing (e.g., "dbgap_study_accession").
"""

import logging
import re
from urllib.parse import urlencode

import jsonschema
import requests
from anvil_consortium_manager.models import BaseWorkspaceData, ManagedGroup
from django.conf import settings
from django.core.exceptions import ValidationError
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
    dbgap_phs = models.PositiveIntegerField(
        verbose_name=" dbGaP phs",
        validators=[MinValueValidator(1)],
        unique=True,
        help_text="""The dbGaP study accession integer associated with this workspace (e.g., 7 for phs000007).""",
    )
    study = models.ForeignKey(
        Study,
        verbose_name="study",
        on_delete=models.PROTECT,
        help_text="The study associated with this dbGaP study accession.",
    )
    history = HistoricalRecords()

    class Meta:
        # Add a white space to prevent autocapitalization fo the "d" in "dbGaP".
        verbose_name = " dbGaP study accession"
        verbose_name_plural = " dbGaP study accessions"

    def __str__(self):
        return "phs{phs:06d} - {study}".format(
            phs=self.dbgap_phs, study=self.study.short_name
        )

    def get_absolute_url(self):
        return reverse(
            "dbgap:dbgap_study_accessions:detail", kwargs={"dbgap_phs": self.dbgap_phs}
        )


class dbGaPWorkspace(DataUseOntologyModel, TimeStampedModel, BaseWorkspaceData):
    """A model to track additional data about dbGaP data in a workspace."""

    # PositiveIntegerField allows 0 and we want this to be 1 or higher.
    # We'll need to add a separate constraint.
    dbgap_study_accession = models.ForeignKey(
        dbGaPStudyAccession,
        verbose_name=" dbGaP study accession",
        on_delete=models.PROTECT,
    )

    # Should dbgap_study, version and participant set be their own model -- dbGaPStudyVersion?
    # Note that having this -- wec ould have derived data workspaces linking to multiple dbgap study versions.
    dbgap_version = models.PositiveIntegerField(
        verbose_name=" dbGaP version",
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP study version associated with this Workspace.""",
    )

    # Do we want version here?
    dbgap_participant_set = models.PositiveIntegerField(
        verbose_name=" dbGaP participant set",
        validators=[MinValueValidator(1)],
        help_text="""The dbGaP participant set associated with this Workspace.""",
    )
    dbgap_consent_code = models.PositiveIntegerField(
        verbose_name=" dbGaP consent code",
        validators=[MinValueValidator(1)],
        help_text="The numeric code assigned to this consent group by dbGaP",
    )
    dbgap_consent_abbreviation = models.CharField(
        verbose_name=" dbGaP consent abbreviation",
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
        return "{} - {}".format(
            self.get_dbgap_accession(),
            self.dbgap_consent_abbreviation,
        )

    def get_dbgap_accession(self):
        return "phs{phs:06d}.v{v}.p{ps}".format(
            phs=self.dbgap_study_accession.dbgap_phs,
            v=self.dbgap_version,
            ps=self.dbgap_participant_set,
        )

    def get_data_access_requests(self):
        """Get a list of data access requests associated with this dbGaPWorkspace."""
        return dbGaPDataAccessRequest.objects.filter(
            dbgap_phs=self.dbgap_study_accession.dbgap_phs,
            original_version=self.dbgap_version,
            original_participant_set=self.dbgap_participant_set,
            dbgap_consent_code=self.dbgap_consent_code,
        )


class dbGaPApplication(TimeStampedModel, models.Model):
    """A model to track dbGaP applications."""

    principal_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        help_text="The principal investigator associated with on this dbGaP application.",
    )
    dbgap_project_id = models.PositiveIntegerField(
        verbose_name=" dbGaP project id",
        validators=[MinValueValidator(1)],
        unique=True,
        help_text="The dbGaP-assigned project_id for this application.",
    )
    anvil_group = models.OneToOneField(
        ManagedGroup,
        verbose_name=" AnVIL group",
        on_delete=models.PROTECT,
        help_text="The AnVIL managed group that can will access to workspaces under this dbGaP application.",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = " dbGaP application"

    def __str__(self):
        return "{}".format(self.dbgap_project_id)

    def get_absolute_url(self):
        """Return the absolute url for this object."""
        return reverse(
            "dbgap:dbgap_applications:detail",
            kwargs={"dbgap_project_id": self.dbgap_project_id},
        )

    def get_dbgap_dar_json_url(self):
        """Return the dbGaP URL that lists DARs for this application."""
        url_params = {
            "name": "project_report",
            "page": "getreport",
            "mode": "json",
            "filter": ["mode", "project_list"],
            "project_list": str(self.dbgap_project_id),
        }
        url = "https://dbgap.ncbi.nlm.nih.gov/aa/wga.cgi?%s"
        # Doseq means to generate the filter key twice, once for "mode" and once for "project_list"
        return url % urlencode(url_params, doseq=True)


class dbGaPDataAccessSnapshot(TimeStampedModel, models.Model):
    """A model to store period checks of a dbGaP application's data access requests."""

    dbgap_application = models.ForeignKey(
        dbGaPApplication,
        verbose_name="dbGaP application",
        on_delete=models.PROTECT,
        help_text="The dbGaP application associated with this DAR.",
    )
    dbgap_dar_data = models.JSONField(null=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = " dbGaP data access snapshot"

    def __str__(self):
        """String method."""
        return "{} - {}".format(self.dbgap_application, self.created)

    def clean(self):
        """Perform custom model cleaning.

        * Check that json_dar_schema validates properly.
        """
        if self.dbgap_dar_data:
            try:
                jsonschema.validate(
                    self.dbgap_dar_data, constants.json_dar_schema_one_project
                )
            except jsonschema.exceptions.ValidationError as e:
                # Replace the full json string because it will be very long
                error_message = e.message.replace(str(e.instance), "JSON array")
                raise ValidationError({"dbgap_dar_data": error_message})
            if (
                self.dbgap_dar_data["Project_id"]
                != self.dbgap_application.dbgap_project_id
            ):
                raise ValidationError(
                    "Project_id in JSON does not match dbgap_application.dbgap_project_id."
                )

    def get_absolute_url(self):
        return reverse(
            "dbgap:dbgap_applications:dbgap_data_access_snapshots:detail",
            kwargs={
                "dbgap_project_id": self.dbgap_application.dbgap_project_id,
                "dbgap_data_access_snapshot_pk": self.pk,
            },
        )

    def create_dars_from_json(self):
        """Add DARs for this application from the dbGaP json for this project snapshot.

        This function loops through the studies and requests in the JSON for this snapshot
        and adds individual dbGaPDataAccessRequests for each one. Because dbGaP does not
        give us the original version and participant set that the DAR grants access to, we
        need to look that up when adding the first DAR with a specific DAR/dbgap_dar_id.
        For new DARs with the same DAR/dbgap_dar_id, we can look up the original version/
        participant set from the previous dbGaPDataAccessRequest.
        """
        # Validate the json. It should already be validated, but it doesn't hurt to check again.
        jsonschema.validate(self.dbgap_dar_data, constants.json_dar_schema_one_project)
        # Log the json.
        msg = "Creating DARs using snapshot pk {pk}...\n".format(
            pk=self.pk,
        )
        logger.info(msg)
        project_json = self.dbgap_dar_data
        # Create a list in which to store DARs to create.
        dars = []
        # Make sure that the dbgap_project_id matches.
        project_id = project_json["Project_id"]
        if project_id != self.dbgap_application.dbgap_project_id:
            raise ValueError(
                "project_id does not match dbgap_application.dbgap_project_id."
            )
        # Loop over studies and requests to create DARs.
        # Do not save them until everything has been successfully created.
        for study_json in project_json["studies"]:
            # Consider making this a model manager method for dbGaPStudyAccession, since it may be common.
            # Get the dbGaPStudyAccession associated with this phs.
            phs = int(
                re.match(constants.PHS_REGEX, study_json["study_accession"]).group(
                    "phs"
                )
            )
            # Create the DAR.
            for request_json in study_json["requests"]:
                # dbGaP does not keep track of the original version and participant set associated with a DAR.
                # Therefore, we need to get it ourselves.
                # Try looking up the original version and participant set from a previous DAR.
                try:
                    # This assumes that a DAR/dbgap_dar_id remains the same for the same phs and consent code.
                    previous_dar = dbGaPDataAccessRequest.objects.filter(
                        dbgap_dar_id=request_json["DAR"]
                    ).latest("created")
                    # Make sure that excepted values match.
                    # Is ValueError the best error to raise?
                    if previous_dar.dbgap_phs != phs:
                        raise ValueError("dbgap_phs mismatch")
                    if previous_dar.dbgap_consent_code != request_json["consent_code"]:
                        raise ValueError("dbgap_consent_code mismatch")
                    if (
                        previous_dar.dbgap_data_access_snapshot.dbgap_application.dbgap_project_id
                        != project_id
                    ):
                        raise ValueError("project_id mismatch")
                    # If everything looks good, pull the original version and participant set from the previous DAR.
                    original_version = previous_dar.original_version
                    original_participant_set = previous_dar.original_participant_set
                except dbGaPDataAccessRequest.DoesNotExist:
                    # If we don't have info about it from a previous DAR, query dbGaP to get the current
                    # version and participant set numbers for this phs.
                    # This url should resolve to url for the current version/participant set.
                    response = requests.get(
                        constants.DBGAP_STUDY_URL,
                        params={"study_id": "phs{phs:06d}".format(phs=phs)},
                        allow_redirects=False,
                    )
                    # Raise an error if an error code was returned.
                    response.raise_for_status()
                    full_accession = response.next.url.split("study_id=")[1]
                    match = re.match(constants.FULL_ACCESSION_REGEX, full_accession)
                    original_version = int(match.group("version"))
                    original_participant_set = int(match.group("participant_set"))
                except ValueError as e:
                    # Log an error and re-raise.
                    msg = "DAR ID mismatch for snapshot pk {} and DAR ID {}".format(
                        self.pk, previous_dar.dbgap_dar_id
                    )
                    logger.error(msg)
                    logger.error(str(e))
                    raise

                dar = dbGaPDataAccessRequest(
                    dbgap_dar_id=request_json["DAR"],
                    dbgap_data_access_snapshot=self,
                    dbgap_phs=phs,
                    original_version=original_version,
                    original_participant_set=original_participant_set,
                    dbgap_consent_code=request_json["consent_code"],
                    dbgap_consent_abbreviation=request_json["consent_abbrev"],
                    dbgap_current_status=request_json["current_DAR_status"],
                )
                dar.full_clean()
                dars.append(dar)
        # Create the DARs in bulk - there are usually a lot of them.
        dars = dbGaPDataAccessRequest.objects.bulk_create(dars)
        return dars


class dbGaPDataAccessRequest(TimeStampedModel, models.Model):
    """A model to track dbGaP data access requests.

    This model is not entirely normalized, since the dbgap_dar_id, dbgap_phs, and dbgap_consent_code
    are likely constant and should not change. original_version, dbgap_participant_set, dbgap_current_status,
    dgap_consent_abbreviation are expected to change with each new dbGaPDataAccessSnapshot. However, we
    have no guarantee that this is true and we are pulling directly from the JSON from dbGaP. In that case,
    it might be safer to store redundant information.

    Note that original_version and dbgap_participant set do *not* from the JSON; see the
    dbGaPDataAccessSnapshot.create_dars_from_json method for details about how they are obtained.
    """

    # The value here is what appears in the DAR JSON from dbGaP.
    # These are the values I've seen so far.
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

    dbgap_data_access_snapshot = models.ForeignKey(
        dbGaPDataAccessSnapshot,
        verbose_name="dbGaP data access snapshot",
        on_delete=models.CASCADE,
        help_text="The dbGaP data access snapshot from which this record came.",
    )
    dbgap_dar_id = models.PositiveIntegerField(
        verbose_name=" dbGaP DAR id",
        validators=[MinValueValidator(1)],
    )
    dbgap_phs = models.PositiveIntegerField(
        verbose_name=" dbGaP study accession phs",
        validators=[MinValueValidator(1)],
        help_text="The phs number of the study accession that this DAR grants access to.",
    )
    original_version = models.PositiveIntegerField(
        verbose_name=" dbGaP version",
        validators=[MinValueValidator(1)],
        help_text="The original version of the dbGaP study accession that this application grants access to.",
    )
    original_participant_set = models.PositiveIntegerField(
        verbose_name=" dbGaP participant set",
        validators=[MinValueValidator(1)],
        help_text="The original participant set of the dbGaP study accession that this application grants access to.",
    )
    dbgap_consent_code = models.PositiveIntegerField(
        verbose_name=" dbGaP consent code",
        validators=[MinValueValidator(1)],
        help_text="The numeric code assigned to this consent group by dbGaP",
    )
    dbgap_consent_abbreviation = models.CharField(
        verbose_name=" dbGaP consent abbreviation",
        max_length=31,
        help_text="The abbreviation for this consent group.",
    )
    dbgap_current_status = models.CharField(
        verbose_name=" dbGaP current status",
        max_length=31,
        choices=DBGAP_CURRENT_STATUS_CHOICES,
    )

    history = HistoricalRecords()

    objects = managers.dbGaPDataAccessRequestManager()

    class Meta:
        verbose_name = " dbGaP data access request"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dbgap_data_access_snapshot",
                    "dbgap_phs",
                    "dbgap_consent_code",
                ],
                name="unique_dbgap_data_access_request",
            ),
            models.UniqueConstraint(
                fields=[
                    "dbgap_data_access_snapshot",
                    "dbgap_dar_id",
                ],
                name="unique_dbgap_data_access_dar_id",
            ),
        ]

    def __str__(self):
        return "{}".format(self.dbgap_dar_id)

    @property
    def is_approved(self):
        return self.dbgap_current_status == self.APPROVED

    def get_dbgap_workspace(self):
        """Get a dbGaPWorkspace associated with this data access request.

        This checks that the dbGaP study accession, version, and participant set match between the
        dbGaPDataAccessRequest and the dbGaPWorkspace."""
        # We may need to modify this to match the DAR version *or greater*, and DAR participant set *or larger*.
        study_accession = dbGaPStudyAccession.objects.get(dbgap_phs=self.dbgap_phs)
        dbgap_workspace = study_accession.dbgapworkspace_set.get(
            dbgap_version=self.original_version,
            dbgap_participant_set=self.original_participant_set,
            dbgap_consent_code=self.dbgap_consent_code,
        )
        return dbgap_workspace

    def has_access(self):
        """Check if the dbGaPApplication associated with this DAR has access to the matching dbGaP workspace."""
        # Check if there is a matching workspace.
        dbgap_workspace = self.get_dbgap_workspace()
        return dbgap_workspace.workspace.has_access(
            self.dbgap_data_access_snapshot.dbgap_application.anvil_group
        )
