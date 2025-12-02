CDSA
======================================================================

The CDSA app tracks signed Consortium Data Sharing Agreements (CDSAs), workspaces containing CDSA data, and access to those workspaces for the PRIMED consortium.

Models
------

Consortium Data Sharing Agreements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following models track information about consortium data sharing agreement versions.

    1. :class:`~primed.cdsa.models.AgreementMajorVersion` - A major version of the CDSA (e.g., version 1, version 2, etc.). New major versions require any agreements using previous CDSA versions to be re-signed.

    2. :class:`~primed.cdsa.models.AgreementVersion` - A specific version of the agreement, including minor versions (e..g, version 1.1, version 1.2, version 2.1, etc.). New minor versions do not require re-signing.

Signed CDSAs
~~~~~~~~~~~~

The following model tracks information about CDSAs that have been signed by consortium members.

    1. :class:`~primed.cdsa.models.SignedAgreement` - A record of a signed CDSA by a user, including the version signed, the signing institution and representative, the date it was signed, and the current status of the agreement (Active, Withdrawn, Lapsed, or Replaced). Each ``SignedAgreement`` is associated with a signed agreement type (e.g., member, data affiliate, or non-data affiliate). Signed Agreements are not complete without an associated agreement type model.

    2. :class:`~primed.cdsa.models.MemberAgreement` - A model that tracks information specific to Member Agreements (e.g., the study site).

    3. :class:`~primed.cdsa.models.DataAffiliateAgreement` - A model that tracks information specific to Data Affiliate Agreements (e.g., the associated study, additional data use limitations, and whether study review is required).

    4. :class:`~primed.cdsa.models.NonDataAffiliateAgreement` - A model that tracks information specific to Non-Data Affiliate Agreements (e.g., the affiliation of the representative).

Each :class:`~primed.cdsa.models.SignedAgreement` is associated with the users who are approved for data access under the agreement (:attr:`~primed.cdsa.models.SignedAgreement.accessors`). The model also has a :attr:`~primed.cdsa.models.SignedAgreement.anvil_access_group` that is intended to contain the AnVIL accounts of the approved accessors.

Furthermore, :class:`~primed.cdsa.models.DataAffiliateAgreement`s also track the set of users that are approved to upload data for the associated study (:attr:`~primed.cdsa.models.DataAffiliateAgreement.uploaders`). They also have a similar AnVIL group (:attr:`~primed.cdsa.models.DataAffiliateAgreement.anvil_upload_group`) that is intended to contain the AnVIL accounts of the approved uploaders.

Workspaces
~~~~~~~~~~

The following models track information about CDSA workspaces.

    1. :class:`~primed.cdsa.models.CDSAWorkspace` - A workspace on AnVIL containing CDSA data. This model tracks the associated study (:class:`~primed.primed_anvil.models.Study`), additional data use limitations, acknowledgments, and whether GSR posting is restricted to controlled-access only. Note that the model is not directly linked to the :class:`~primed.cdsa.models.DataAffiliateAgreement` for the associated study, as multiple agreements may exist for a given study, especially when AgreementMajorVersions increment.


CDSA accessors and uploaders
----------------------------

Each :class:`~primed.cdsa.models.SignedAgreement` tracks the set of accessors that have been specified for the agreement.


Auditing accessors
~~~~~~~~~~~~~~~~~~

The app provides functionality (:class:`~primed.cdsa.audit.accessor_audit.AccessorAudit`) to audit the members of the SignedAgreement's :attr:`~primed.cdsa.models.SignedAgreement.anvil_access_group` against the set of accessors specified for the agreement.
Accessors are considered to be covered under the agreement can be added to the access group if all of the following are true:

    - The user is listed as an accessor under the Signed Agreement. Note that the signing representative is not automatically considered as an accessor unless they are explicitly listed.
    - The user has a linked AnVIL account
    - The user's AnVIL account is active


The :class:`~primed.cdsa.audit.accessor_audit.AccessorAudit` auditing class is responsible for performing the above checks and storing the results.
The audit must be run for all ``SignedAgreements`` together.
For each agreement, it checks both the set of listed accessors as well as any current members of the agreement's ``anvil_access_group``.

The following results are possible:

    - :class:`~primed.cdsa.audit.accessor_audit.VerifiedAccess` - The user is listed as an accessor for the agreement, and is a member of the agreement's ``anvil_access_group``.
    - :class:`~primed.cdsa.audit.accessor_audit.VerifiedNoAccess` - The user is not listed as an accessor under the agreement and is not a member of the agreement's ``anvil_access_group``.
    - :class:`~primed.cdsa.audit.accessor_audit.GrantAccess` - The user is listed as an accessor on the agreement, but is not a member of the agreement's ``anvil_access_group``. Action is needed to add the user to the access group.
    - :class:`~primed.cdsa.audit.accessor_audit.RemoveAccess` - The user is not listed as an accessor on the agreement, but is a member of the agreement's ``anvil_access_group``. Action is needed to remove the user from the access group.
    - :class:`~primed.cdsa.audit.accessor_audit.Error` - An unexpected situation occurred and further exploration is necessary (e.g., a group is a member of the agreement's ``anvil_access_group``).

Viewing audit results
`````````````````````

The access audit can be run and viewed interactively via the :class:`~primed.cdsa.views.AccessorAudit` view.
This view can be accessed by navigating to "CDSA > Audit accessors" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each agreement/workspace pair.

    - "Verified" table: all records with :class:`~primed.cdsa.audit.accessor_audit.VerifiedAccess` and :class:`~primed.cdsa.audit.accessor_audit.VerifiedNoAccess` results.
    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., an accessor recently linked their AnVIL account). To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the user's account to/from agreement's ``anvil_access_group``.

    - "Errors" table: all records with :class:`~primed.cdsa.audit.accessor_audit.Error` results (e.g., a group is a member of the agreement's ``anvil_access_group``)


Auditing uploaders
~~~~~~~~~~~~~~~~~~

The app provides similar functionality for auditing uploaders for a single :class:`~primed.cdsa.models.DataAffiliateAgreement`. Documentation is the same as above, except uploaders are added to or removed from the agreement's :attr:`~primed.cdsa.models.DataAffiliateAgreement.anvil_upload_group`.

The audit can be run and viewed interactively via the :class:`~primed.cdsa.views.UploaderAudit` view ("CDSA > Audit uploaders" in the navbar.)



Workspace Access
----------------

The CDSA app contains logic to track access to workspaces containing CDSA data.

By signing the CSDA, users are approved for data access to all data provided by the CDSA, instead of piecemeal access to a subset of CDSA data.

To implement this policy in practice, a single Mangaed Group should be created on AnVIL.
This group should contain the :attr:`~primed.cdsa.models.SignedAgreement.anvil_access_group` of all Active :class:`~primed.cdsa.models.SignedAgreement`s.
The name of the group can be set in the settings file (``settings.ANVIL_CDSA_GROUP_NAME``) for the project.


Auditing access to workspaces
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CDSA app contains auditing code (:class:`~primed.cdsa.audit.access_audit.WorkspaceAccessAudit`) to check whether the ``settings.ANVIL_CDSA_GROUP_NAME`` group should have access to a given workspace.
These audits help ensure that CDSA data is only accessible to approved users and reduce human error.
The app also provides convenient views and management commands to run the audits and view the results.

CDSA access to a given ``CDSAWorkspace`` can be granted if:

    - The study associated with the workspace has a corresponding :class:`~primed.cdsa.models.DataAffiliateAgreement`.
    - The ``DataAffiliateAgreement`` is the **primary** agreement for the study.
    - The ``DataAffiliateAgreement`` has status **Active**.

The :class:`~primed.cdsa.audit.access_audit.WorkspaceAccessAudit` auditing class is responsible for performing the above checks and storing the results.
The audit can be run for all CDSA workspaces together or for a single workspace at a time.
For each workspace, it will create a result instance indicating if access to the workspace is correct or if any action that needs to be taken to correct access.
The following results are possible:

    - :class:`~primed.cdsa.audit.access_audit.VerifiedAccess` - The workspace meets all criteria for CDSA access and the ``settings.ANVIL_CDSA_GROUP_NAME`` group is in the workspace's auth domain.
    - :class:`~primed.cdsa.audit.access_audit.VerifiedNoAccess` - The workspace **does not** meet all criteria for CDSA access and the ``settings.ANVIL_CDSA_GROUP_NAME`` group is not in the workspace's auth domain.
    - :class:`~primed.cdsa.audit.access_audit.GrantAccess` - The workspace meets all criteria for CDSA access and the ``settings.ANVIL_CDSA_GROUP_NAME`` group is **not** in the workspace's auth domain. Action is needed to add the group to the workspace's auth domain.
    - :class:`~primed.cdsa.audit.access_audit.RemoveAccess` - The workspace **does not** meet all criteria for CDSA access and the ``settings.ANVIL_CDSA_GROUP_NAME`` group is in the workspace's auth domain. Action is needed to remove the group from the workspace's auth domain.

Viewing audit results
`````````````````````

The access audit can be run and viewed interactively via the :class:`~primed.csda.views.CDSAWorkspaceAudit` view.
This view can be accessed by navigating to "CDSA > Audit workspaces" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each agreement/workspace pair.

    - "Verified" table: all records with :class:`~primed.csda.audit.access_audit.VerifiedAccess` and :class:`~primed.csda.audit.access_audit.VerifiedNoAccess` results.

    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., the data affiliate agreement was withdrawn). To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the agreement's ``anvil_access_group`` to/from the workspace's auth domain as appropriate.

    - "Errors" table: all records with :class:`~primed.csda.audit.access_audit.OtherError` results (e.g., no primary agreement was ever signed for this study).

Uploader access
~~~~~~~~~~~~~~~

Contrary to accessors, uploaders are only approved to access data for the specific workspaces from their study, not all CDSA workspaces.

In order to access a workspaces, uploaders are also required to be listed as accessors on an Active :class:`~primed.cdsa.models.SignedAgreement`.
In practice, this is typically the same :class:`~primed.cdsa.models.DataAffiliateAgreement` that lists them as an uploader, but it is not required to be the case.

During the data preparation process, the CDSA workspace is shared directly withthe uploader group as a writer with ``can_compute`` permission.
Once data preparation is complete, this permission is removed.
There are currently no audits that check for access, so this process is manual (but is similar to the process for handling workspace sharing during data preparation for other workspace types).


Auditing access for SignedAgreements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CDSA app contains auditing code to check whether the ``anvil_access_group`` for a SignedAgreement should be part of the the ``settings.ANVIL_CDSA_GROUP_NAME`` Managed Group group on AnVIL.
These audits help ensure that CDSA data is only accessible to approved users and reduce human error.
The app also provides convenient views and management commands to run the audits and view the results.

A Signed Agreement's ``anvil_access_group`` should be part of the ``settings.ANVIL_CDSA_GROUP_NAME`` Managed Group if the SignedAgreement meets all of the following criteria:

    - The ``SignedAgreement`` has **Active** status.
    - The ``SignedAgreement`` is a primary agreement, or has an associated primary agreement with **Active** status.

The :class:`~primed.cdsa.audit.access_audit.SignedAgreementAccessAudit` auditing class is responsible for performing the above checks and storing the results.
The audit can be run for all ``SignedAgreements`` together or for a single agreement at a time.
For each ``SignedAgreement``, it will create a result instance indicating if membership in the ``settings.ANVIL_CDSA_GROUP_NAME`` group is correct or if any action needs to be taken to correct membership.
The following results are possible:

    - :class:`~primed.cdsa.audit.signed_agreement_audit.VerifiedAccess` - The ``SignedAgreement`` meets all criteria for CDSA access and its ``anvil_access_group`` is a member of ``settings.ANVIL_CDSA_GROUP_NAME`` group.
    - :class:`~primed.cdsa.audit.signed_agreement_audit.VerifiedNoAccess` - The ``SignedAgreement`` **does not** meet all criteria for CDSA access and its ``anvil_access_group`` is **not** a member of ``settings.ANVIL_CDSA_GROUP_NAME`` group.
    - :class:`~primed.cdsa.audit.signed_agreement_audit.GrantAccess` - The ``SignedAgreement`` meets all criteria for CDSA access and its ``anvil_access_group`` is **not** a member of ``settings.ANVIL_CDSA_GROUP_NAME`` group. Action is needed to add the ``anvil_access_group`` to the ``settings.ANVIL_CDSA_GROUP_NAME`` group.
    - :class:`~primed.cdsa.audit.signed_agreement_audit.RemoveAccess` - The ``SignedAgreement`` **does not** meets all criteria for CDSA access and its ``anvil_access_group`` is a member of ``settings.ANVIL_CDSA_GROUP_NAME`` group. Action is needed to remove the ``anvil_access_group`` from the ``settings.ANVIL_CDSA_GROUP_NAME`` group.

Viewing audit results
`````````````````````

The access audit can be run and viewed interactively via the :class:`~primed.csda.views.SignedAgreementAudit` view.
This view can be accessed by navigating to "CDSA > Audit signed agreements" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each agreement/workspace pair.

    - "Verified" table: all records with :class:`~primed.csda.audit.signed_agreement_audit.VerifiedAccess` and :class:`~primed.csda.audit.signed_agreement_audit.VerifiedNoAccess` results.

    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., an agreement is no longer active). To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the agreement's ``anvil_access_group`` to/from the ``settings.ANVIL_CDSA_GROUP_NAME`` group as appropriate.

    - "Errors" table: all records with :class:`~primed.csda.audit.signed_agreement_audit.OtherError` results. There is currently no situation where this would occur in the code.


Viewing CDSA records
--------------------

The app provides publicly-accessible views to show current CDSA records and access.

These views can be accessed by navigating to "CDSA > View CDSA records" in the navbar.

The following views are provided:

    - Representatives: The list of signing representatives for all Active :class:`~primed.cdsa.models.SignedAgreement` objects, along with their CDSA role, their institution, and the version of the agreement that was signed.
    - Studies: The list of studies associated iwth currently-active ``DataAffiliateAgreement``s, and the associated signing representative.
    - User access: The list of named accessors on any active ``SignedAgreement``, along with the associated agreement's institution and signing representative.
    - Workspaces: The list of workspaces on AnVIL that contain CDSA data, along with consent information and when the workspace was shared with the consortium.


Management commands and cron jobs
---------------------------------

The CDSA app provides a management command (``run_csda_audit``) that runs the following audits:

    - :class:`~primed.dbgap.audit.workspace_audit.WorkspaceAccessAudit`
    - :class:`~primed.dbgap.audit.signed_agreement_audit.SignedAgreementAudit`
    - :class:`~primed.dbgap.audit.accessor_audit.AccessorAudit`
    - :class:`~primed.dbgap.audit.uploader_audit.UploaderAudit`

It also provides a management command to export CDSA records into text files for longer-term recordkeeping.


Both management commands run weekly via a cron job (see `primed_apps.cron <https://github.com/UW-GAC/primed-django/blob/main/primed_apps.cron>`_).
