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
