from itertools import groupby

import pandas as pd
from anvil_consortium_manager.models import ManagedGroup, WorkspaceGroupSharing
from django.db.models import CharField, Exists, F, OuterRef, Value
from django.db.models.functions import Concat

from primed.cdsa.models import CDSAWorkspace
from primed.dbgap.models import dbGaPWorkspace
from primed.miscellaneous_workspaces.models import OpenAccessWorkspace

from .models import AvailableData


def get_summary_table_data():
    """Get data for the summary table."""

    # If no available data objects exist, raise ???.
    available_data_types = AvailableData.objects.values_list("name", flat=True)
    if not len(available_data_types):
        raise RuntimeError(
            "get_summary_table_data requires at least one AvailableData object to exist."
        )

    # This query will be used to add information about whether a study has workspaces
    # that are shared with the consortium.
    shared = WorkspaceGroupSharing.objects.filter(
        group__name="PRIMED_ALL",
        workspace=OuterRef("workspace__pk"),
    )

    # Query for dbGaPWorkspaces.
    dbgap = dbGaPWorkspace.objects.annotate(
        access_mechanism=Value("dbGaP"),
        is_shared=Exists(shared),
    ).values(
        "is_shared",
        "access_mechanism",
        # Rename columns to have the same names.
        workspace_name=F("workspace__name"),
        study_name=F("dbgap_study_accession__studies__short_name"),
        data=F("available_data__name"),
    )
    df_dbgap = pd.DataFrame.from_dict(dbgap)

    # Query for OpenAccessWorkspaces.
    open = OpenAccessWorkspace.objects.annotate(
        access_mechanism=Value("Open access"),
        is_shared=Exists(shared),
    ).values(
        "is_shared",
        "access_mechanism",
        # Rename columns to have the same names.
        workspace_name=F("workspace__name"),
        study_name=F("studies__short_name"),
        data=F("available_data__name"),
    )
    df_open = pd.DataFrame.from_dict(open)

    # Query for CDSAWorkspaces.
    cdsa = CDSAWorkspace.objects.annotate(
        access_mechanism=Value("CDSA"),
        is_shared=Exists(shared),
    ).values(
        "is_shared",
        "access_mechanism",
        # Rename columns to have the same names.
        workspace_name=F("workspace__name"),
        study_name=F("study__short_name"),
        data=F("available_data__name"),
    )
    df_cdsa = pd.DataFrame.from_dict(cdsa)

    # This union may not work with MySQL < 10.3:
    # https://code.djangoproject.com/ticket/31445
    # qs = dbgap.union(open)
    #
    # # If there are no workspaces, return an empty list.
    # if not qs.exists():
    #     return []
    #
    # # Otherwise, start making the summary table.
    # df = pd.DataFrame.from_dict(qs)

    # Instead combine in pandas.
    df = pd.concat([df_cdsa, df_dbgap, df_open])

    # If there are no workspaces, return an empty list.
    if df.empty:
        return []

    # Sort by specific columns
    df = df.sort_values(by=["study_name", "access_mechanism"])
    # Concatenate multiple studies into a single comma-delimited string.
    df = (
        df.groupby(
            ["workspace_name", "data", "is_shared", "access_mechanism"],
            dropna=False,
        )["study_name"]
        .apply(lambda x: ", ".join(x))
        .reset_index()
        .drop("workspace_name", axis=1)
    )
    # Replace None/NaNs with a dummy column for pivoting.
    # If we don't do this, data can sometimes get dropped.
    df["data"] = df["data"].fillna("no_data")
    # Pivot so that the available data types are their own columns.
    data = (
        pd.pivot_table(
            df,
            index=["study_name", "is_shared", "access_mechanism"],
            columns=["data"],
            # set this to len to count the number of workspaces instead of returning a boolean value.
            aggfunc=lambda x: len(x) > 0,
            fill_value=False,
            # aggfunc=len,
            # fill_value=0,
        )
        .rename_axis(columns=None)
        .reset_index()
        .rename(columns={"study_name": "study", "B": "c"})
    )
    # Remove the dummy "no_data" column if it exists.
    if "no_data" in data:
        data = data.drop("no_data", axis=1)
    # Add columns for data types that have no workspaces in this list.
    for available_data in available_data_types:
        if available_data not in data:
            data[available_data] = False
    # Convert to a list of dictionaries for passing to the django-tables2 table.
    data = data.to_dict(orient="records")
    return data


def get_workspaces_for_phenotype_inventory():
    """Get input to the primed-phenotype-inventory workflow.

    This function generates the input for the "workspaces" field of the primed-phenotype-inventory workflow. Only
    workspaces that have been shared with the consortium are included.
    See dockstore link: https://dockstore.org/workflows/github.com/UW-GAC/primed-inventory-workflows/primed_phenotype_inventory:main?tab=info

    The "workspaces" field has the format:
    {
        "billing-project-1/workspace-1": "study1, study2",
        "billing-project-2/workspace-2": "study3",
        ...
    }
    """  # noqa: E501

    # primed-all group. We will need this to determine if the workspace is shared with PRIMED_ALL.
    primed_all = ManagedGroup.objects.get(name="PRIMED_ALL")

    dbgap_workspaces = (
        dbGaPWorkspace.objects.filter(
            # Just those that are shared with PRIMED_ALL.
            workspace__workspacegroupsharing__group=primed_all,
        )
        .annotate(
            workspace_name=Concat(
                F("workspace__billing_project__name"),
                Value("/"),
                F("workspace__name"),
                output_field=CharField(),
            ),
            study_names=F("dbgap_study_accession__studies__short_name"),
        )
        .values(
            # "workspace",
            # "workspace_billing_project",
            "workspace_name",
            "study_names",
        )
    )

    cdsa_workspaces = (
        CDSAWorkspace.objects.filter(
            # Just those that are shared with PRIMED_ALL.
            workspace__workspacegroupsharing__group=primed_all,
        )
        .annotate(
            workspace_name=Concat(
                F("workspace__billing_project__name"),
                Value("/"),
                F("workspace__name"),
                output_field=CharField(),
            ),
            study_names=F("study__short_name"),
        )
        .values(
            "workspace_name",
            "study_names",
        )
    )

    open_access_workspaces = (
        OpenAccessWorkspace.objects.filter(
            # Just those that are shared with PRIMED_ALL.
            workspace__workspacegroupsharing__group=primed_all,
        )
        .annotate(
            workspace_name=Concat(
                F("workspace__billing_project__name"),
                Value("/"),
                F("workspace__name"),
                output_field=CharField(),
            ),
            study_names=F("studies__short_name"),
        )
        .values(
            "workspace_name",
            "study_names",
        )
    )

    # Combine all querysets and process into the expected output for the AnVIL workflow.
    workspaces = dbgap_workspaces.union(cdsa_workspaces).union(open_access_workspaces)

    json = {}
    for key, group in groupby(workspaces, lambda x: x["workspace_name"]):
        study_names = [x["study_names"] if x["study_names"] else "" for x in group]
        if not study_names:
            study_names = ""
        json[key] = ", ".join(sorted(study_names))

    return json
