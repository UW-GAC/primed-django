Shared behavior (primed_anvil)
======================================================================

Workspace access
----------------

The general strategy for workspace access in PRIMED is to share data storage workspaces
(e.g., :class:`~primed.dbgap.models.dbGaPWorkspace`, :class:`~primed.cdsa.models.CDSAWorkspace`, :class:`~primed.miscellaneous_workspaces.models.OpenAccessWorkspace`)
with the full consortium (via ``PRIMED_ALL``)
but only add users with approved access to the workspace's authorization domain (if applicable).
This allows users to see that the workspace exists, but only those with access can actually use it.

Other workspace types (e.g., :class:`~primed.collaborative_analysis.models.CollaborativeAnalysisWorkspace`) use a different sharing and access strategy, which (if applicable) will be detailed in the specific app's documentation.


Account linking and verification
--------------------------------

All PRIMED members are allowed to link their AnVIL accounts via the web app.
After a user verifies their account, the account is automatically added to the following groups:

    - The ``member_group`` associated with all :class:`~primed.primed_anvil.models.StudySite` objects that they are part of
    - The ``anvil_access_group`` associated with all :class:`~primed.dbgap.models.dbGaPApplication` objects for which the user is a PI or collaborator
    - The ``anvil_access_group`` associated with all :class:`~primed.cdsa.models.SignedAgreement` objects for which the user is a named accessor
    - The ``anvil_upload_group`` associated with all :class:`~primed.cdsa.models.DataAffiliateAgreement` objects for which the user is a named uploader

The notification email to the CC contains the list of groups that the account has automatically been added to.
