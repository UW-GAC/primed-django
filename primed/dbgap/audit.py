# Auditing for dbGaP workspace access.

# For a given managed group:
# - do they have access to all the workspaces they should?
# - do they have access to any workspaces they shouldn't?
#   - if not, for expected reasons?
#
# Cases:
# - An application has an approved DAR to a workspace and has access.
#   - Show add access button.
# - An application has an approved DAR to a workspace and does not have access because the DAR was updated.
#   - Show add access button.
# - An application has an approved DAR to a workspace and does not have access because the workspace was just created.
#   - Show Add access button.
# - An application does not have an approved DAR to a workspace and does not have access.
#   - PROBLEM.
# - An application does not have an approved DAR to a workspace and has access because the DAR was updated.
#   - Show remove access button.
