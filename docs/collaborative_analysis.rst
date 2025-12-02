Collaborative analysis
======================================================================

The ``collaborative_analysis`` app tracks workspaces created for cross-site collaborative analysis.
The sharing strategy for these workspaces is different than the standard sharing strategy for most workspaces in PRIMED (see :ref:`primed_anvil`).

Workspaces
------

The following models track information about dbGaP study accessions and workspaces.

1. :class:`~primed.collaborative_analysis.models.CollaborativeAnalysisWorkspace` - A workspace on AnVIL intended for cross-site analysis using multiple data sources.

Each workspace of this type is associated with a set of workspaces containing source data to be used in analyses.
These workspaces could be of different types (e.g., :class:`~primed.dbgap.models.dbGaPWorkspace`, :class:`~primed.cdsa.models.CDSAWorkspace`, :class:`~primed.miscellaneous_workspaces.models.OpenAccessWorkspace`), but should generally be data storage workspaces.
Each ``CollaborativeAnalysisWorkspace`` has a "custodian" (:attr:`~primed.collaborative_analysis.models.CollaborativeAnalysisWorkspace.custodian`) who is responsible for ensuring that the workspace is being used appropriately and that the source workspaces are correct.
The custodian is typically the person who requested the workspace for analysis.

Access to Collaborative Analysis workspaces
-------------------------------------------

:class:`~primed.collaborative_analysis.models.CollaborativeAnalysisWorkspace` objects have an associated Managed Group on AnVIL (:attr:`~primed.collaborative_analysis.models.CollaborativeAnalysisWorkspace.analyst_group`) that contains the AnVIL accounts of analysts specified by the custodian.
A PRIMED user is allowed to work in the Collaborative Analysis workspace if the following are all true:

    - The analyst has access to all source workspaces associated with the Collaborative Analysis workspace
    - The analyst's AnVIL account is active
    - The analyst is a member of the workspace's ``analyst_group`` (e.g., has been specified by the custodian as an analyst)

To manage access to the workspace, analysts are added to the workspace's authorization domain if all of the above criteria are met.
The workspace is then shared with the analyst group with "write" permission.
This means that if an account is in the analyst group but does not have access to all source workspaces, they will see that the workspace exists but will not be able to access it or the data contained within.


Auditing workspace access
~~~~~~~~~~~~~~~~~~~~~~~~~

The app provides functionality (:mod:`primed.collaborative_analysis.audit`) to audit the members of the workspace's authorization domain against the set of analysts in the workspace's ``analyst_group``.
If all of the criteria in the previous section are met, the audit will confirm that the user is in the authorization domain or whether they need to be added; or if any criteria are not met, the audit will confirm that the user is not in the authorization domain or whether they need to be removed.

The :class:`~primed.collaborative_analysis.audit.CollaborativeAnalysisWorkspaceAccessAudit` auditing class is responsible for performing the above checks and storing the results.
The audit can be run for all workspaces or for a single workspace at a time.
For each workspace, it checks both the set of analysts in the ``analyst_group`` as well as any current members of the workspace's authorization domain.

The following results are possible:

- :class:`~primed.collaborative_analysis.audit.VerifiedAccess` - The account meets all criteria for access and is in the workspace authorization domain.
- :class:`~primed.collaborative_analysis.audit.VerifiedNoAccess` - The account **does not** meet all criteria for access and is **not** in the workspace authorization domain.
- :class:`~primed.collaborative_analysis.audit.GrantAccess` - The account meets all criteria for access and is **not** in the workspace authorization domain.
- :class:`~primed.collaborative_analysis.audit.RemoveAccess` - The account **does not** meet all criteria for access and is in the workspace authorization domain.

Viewing audit results
~~~~~~~~~~~~~~~~~~~~~

The access audit can be run and viewed interactively via the :class:`~primed.collaborative_analysis.views.WorkspaceAudit` view.
This view can be accessed by navigating to "Collaborative analysis > Audit access" in the navbar.

The view runs the audit and displays the results in tables, allowing users to easily see the access status for each workspace/analyst pair.

    - "Verified" table: all records with :class:`~primed.collaborative_analysis.audit.VerifiedAccess` and :class:`~primed.collaborative_analysis.audit.VerifiedNoAccess` results.
    - "Action Needed" table: all records where action needs to be taken, but is expected in some way (e.g., an analyst recently lost access to one source workspace)

    To grant or remove access, users can click on the button in the "Action" column of this table to automatically add/remove the application's ``anvil_access_group`` to/from the workspace's auth domain as appropriate.

    - "Errors" table: all records from a situation that is not expected to occur (e.g., an unexpected group is a member of the workspace's authorization domain)


Management commands and cron jobs
---------------------------------

The dbGaP app provides a management command (:class:`~primed.collaborative_analysis.management.commands.run_collaborative_analysis_audit`) that runs the above :class:`~primed.collaborative_analysis.audit.CollaborativeAnalysisWorkspaceAccessAudit` audit for all workspaces.

The audits run weekly via a cron job (see `primed_apps.cron <https://github.com/UW-GAC/primed-django/blob/main/primed_apps.cron>`_).
