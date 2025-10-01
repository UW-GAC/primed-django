dbGaP
======================================================================

The dbGaP app tracks dbGaP applications, workspaces containing dbGaP data, and access to those workspaces for the PRIMED consortium.

Models
------

Workspaces
~~~~~~~~~~

The following models track information about dbGaP study accessions and workspaces.

1. :class:`~primed.dbgap.models.dbGaPStudyAccession` - A dbGaP study accession (e.g., phs000200), without version or participant set.

2. :class:`~primed.dbgap.models.dbGaPWorkspace` - A workspace on AnVIL containing dbGaP data. This model tracks the dbGaP study accession, version, participant set, consent abbreviation (e.g., HMB) and consent code (e.g., 1) for the data in the workspace.

Data Access
~~~~~~~~~~~

The following models track information about dbGaP applications and data access requests.


1. :class:`~primed.dbgap.models.dbGaPApplication` - A PRIMED coordinated dbGaP application submitted by a PI.

2. :class:`~primed.dbgap.models.dbGaPDataAccessSnapshot` - A record of a snapshot of data access for a given dbGaP application at a point in time. Each snapshot contains one or more data access requests (DARs) for a given application.

3. :class:`~primed.dbgap.models.dbGaPDataAccessRequest` - A record of a dbGaP DAR and its status.


Each :class:`~primed.dbgap.models.dbGapApplication` is associated a Managed Group on ANVIL (:attr:`~primed.dbgap.models.dbGaPApplication.anvil_access_group`) that is intended to contain the AnVIL accounts of anyone who should have access to data under this dbGaP application.
Access to ``dbGaPWorkspaces`` is controlled by adding or removing the application's :attr:`~primed.dbgap.models.dbGaPApplication.anvil_access_group` to or from the auth domain of each workspace.
``dbGaPWorkspaces`` are typically shared with the entire consortium, but only approved users will be able to access it due to the auth domain restrictions.

Application collaborators
-------------------------

Each :class:`~primed.dbgap.models.dbGaPApplication` tracks the set of collaborators that have been specified by the PI covered under this application.

Auditing collaborators
~~~~~~~~~~~~~~~~~~~~~~

The app provides functionality (:class:`~primed.dbgap.audit.collaborator_audit.dbGaPCollaboratorAudit`) to audit the members of the dbGaP application's :attr:`~primed.dbgap.models.dbGaPApplication.anvil_access_group` against the set of collaborators specified for the application.
Collaborators are considered to be covered under the application and can be added to the access group if all of the following are true:

- The user is listed as the PI or a collaborator of the dbGaP application
- The user has a linked AnVIL account
- The user's AnVIL account is active


The :class:`~primed.dbgap.audit.collaborator_audit.dbGaPCollaboratorAudit` auditing class is responsible for performing the above checks and storing the results.
The audit can be run for all applications or for a single application at a time.
For each application, it checks both the set of listed collaborators as well as any current members (groups or users) of the application's ``anvil_access_group``.

The following results are possible:

- :class:`~primed.dbgap.audit.collaborator_audit.VerifiedAccess` - The user is covered under the application, and is a member of the application's ``anvil_access_group``.
- :class:`~primed.dbgap.audit.collaborator_audit.VerifiedNoAccess` - The user is not covered under the application (e.g., inactive) and is not a member of the application's ``anvil_access_group``.
- :class:`~primed.dbgap.audit.collaborator_audit.GrantAccess` - The user is covered under the application, but is not a member of the application's ``anvil_access_group``. Action is needed to add the user to the access group.
- :class:`~primed.dbgap.audit.collaborator_audit.RemoveAccess` - The user is not covered under the application, but is a member of the application's ``anvil_access_group``. Action is needed to remove the user from the access group.
- :class:`~primed.dbgap.audit.collaborator_audit.Error` - An unexpected situation occurred and further exploration is necessary. An example of this when another group is a member of the `anvil_access_group`, as a group cannot be listed as a collaborator.

Viewing audit results
~~~~~~~~~~~~~~~~~~~~~

The access audit can be run and viewed interactively via the :class:`~primed.dbgap.views.dbGaPCollaboratorAudit` view.
This view can be accessed by navigating to "dbGaP > Audits dbGaP collaborators" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each application/workspace pair.

    - "Verified" table: all records with :class:`~primed.dbgap.audit.collaborator_audit.VerifiedAccess` and :class:`~primed.dbgap.audit.collaborator_audit.VerifiedNoAccess` results.
    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., a collaborator recently linked their AnVIL account)

    To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the application's ``anvil_access_group`` to/from the workspace's auth domain as appropriate.

    - "Errors" table: all records with :class:`~primed.dbgap.audit.collaborator_audit.Error` results (e.g., a group is a member of the `anvil_access_group`). Typically, resolving these errors requires identifying why the error might have occurred, determining whether it lead to a DMI, and then manually deleting the membership record in ACM.


DARs and workspace access
-------------------------

Updating DARs
~~~~~~~~~~~~~

The dbGaP app contains logic to track DARs and access to workspaces containing dbGaP data.

CC staff must manually create a new DAR snapshot for each dbGaP application (or all applications).
DARs can be updated:

* for all applications: navigate to "dbGaP > Update DARs for all applications",
* for a single application: navigate to the detail page for that dbGaPApplication and click on "Update data access requests".

The form will instruct you on how to proceed.
Upon successful form submission, the system will create a new :class:`~primed.dbgap.models.dbGaPDataAccessSnapshot`.
This snapshot will be marked as the "latest" snapshot for the application(s).

New :class:`~primed.dbgap.models.dbGaPDataAccessRequest` records for each DAR found for the application(s) will be created for this snapshot using the :meth:`~primed.dbgap.models.dbGaPDataAccessSnapshot.create_dars_from_json` method.

If a DAR with the same :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.dbgap_dar_id` already exists for a previous snapshot, a new :class:`~primed.dbgap.models.dbGaPDataAccessRequest` will still be created with the current information from dbGaP.
It will also set the :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.original_version` and :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.original_participant_set` fields on the new DAR record using the values from the previous DAR record.
It also performs some consistency checks between the old record and the new record to verify that both records have the same:

- :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.dbgap_phs`
- :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.dbgap_consent_code`
- ``dbgap_project_id`` as associated with :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.dbgap_data_access_snapshot`

If any of these fields differ between the old and new DAR records, a ``ValueError`` will be raised and a CC staff member will need to investigate to determine the best course of action.

If no DAR with the same ``dbgap_dar_id`` already exists, the method will set the ``original_version`` ``original_participant_set`` by checking dbGaP for the current version of the phs.
To obtain the current version and participant set, it checks the :attr:`primed.dbgap.constants.DBGAP_STUDY_URL` for the phs associated with this DAR.
This website redirects to the currently-released version of the phs on dbGaP.
The code then pulls the version and participant set information from the redirected URL.


Auditing workspace access using DARs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The dbGaP app contains auditing code (:class:`~primed.dbgap.audit.access_audit.dbGaPAccessAudit`) to check which dbGaP Applications have access to PRIMED workspaces containing dbGaP data.
These audits help ensure that dbGaP data is only accessible to approved users and reduce human error.
The app also provides convenient views and management commands to run the audits and view the results.

Access for a given ``dbGaPApplication`` to a given ``dbGaPWorkspace`` can be granted if:

- A DAR exists in the most recent ``dbGaPDataAccessSnapshot`` for the application
- The DAR has the same ``dbgap_phs`` and ``dbgap_consent_code`` as the workspace, the DAR's ``original_version`` is less than or equal to the workspace's ``dbgap_version``, and the DAR's ``original_participant_set`` is less than or equal to than the workspace's ``dbgap_participant_set``
- The DAR's :attr:`~primed.dbgap.models.dbGaPDataAccessRequest.dbgap_current_status` is **approved**

If all of the above are true, then the application has access to the workspace.

The :class:`~primed.dbgap.audit.access_audit.dbGaPAccessAudit` auditing class is responsible for performing the above checks and storing the results.
The audit can be run for all applications and all workspaces, for a single application, or for a single workspace.
For each application/workspace pair, it will create a result instance indicating if the application's access is correct or if any action that needs to be taken to update its access to the workspace.
The following results are possible:

- :class:`~primed.dbgap.audit.access_audit.VerifiedAccess` - The application is approved to access data in the workspace, and its ``anvil_access_group`` is in the workspace's auth domain.
- :class:`~primed.dbgap.audit.access_audit.VerifiedNoAccess` - The application is not approved to access data in the workspace, and its ``anvil_access_group`` is not in the workspace's auth domain.
- :class:`~primed.dbgap.audit.access_audit.GrantAccess` - The application is approved to access data in the workspace, but its ``anvil_access_group`` is not in the workspace's auth domain. Action is needed to add the group to the workspace's auth domain.
- :class:`~primed.dbgap.audit.access_audit.RemoveAccess` - The application is not approved to access data in the workspace, but its ``anvil_access_group`` is in the workspace's auth domain. Action is needed to remove the group from the workspace's auth domain.
- :class:`~primed.dbgap.audit.access_audit.Error` - An unexpected situation occurred and further exploration is necessary (e.g., an application has access but there is no record of an approved DAR at any time in the past)

Viewing audit results
~~~~~~~~~~~~~~~~~~~~~

The access audit can be run and viewed interactively via the :class:`~primed.dbgap.views.dbGaPAccessAuditListView` view.
This view can be accessed by navigating to "dbGaP > Audits dbGaP access" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each application/workspace pair.

    - "Verified" table: all records with :class:`~primed.dbgap.audit.access_audit.VerifiedAccess` and :class:`~primed.dbgap.audit.access_audit.VerifiedNoAccess` results.
    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., a DAR recently was approved for the workspace)
    To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the application's ``anvil_access_group`` to/from the workspace's auth domain as appropriate.

    - "Errors" table: all records with :class:`~primed.dbgap.audit.access_audit.Error` results (e.g., an application never had an approved DAR but is in the auth domain). Typically, resolving these errors requires identifying why the error might have occurred, determining whether it lead to a DMI, and then manually deleting the membership record in ACM.



Management commands and cron jobs
---------------------------------

The dbGaP app provides a management command (:class:`~primed.dbgap.management.commands.run_dbgap_audit`) that runs the above :class:`~primed.dbgap.audit.access_audit.dbGaPAccessAudit` and :class:`~primed.dbgap.audit.collaborator_audit.dbGaPCollaboratorAudit` audits.

The audits run weekly via a cron job (see `primed_apps.cron <https://github.com/UW-GAC/primed-django/blob/main/primed_apps.cron>`_).
