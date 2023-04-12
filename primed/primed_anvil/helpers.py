import pandas as pd
from anvil_consortium_manager.models import WorkspaceGroupSharing
from django.db.models import Exists, F, OuterRef, Value

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

    # This query will be used to annotate the
    shared = WorkspaceGroupSharing.objects.filter(
        group__name="PRIMED_ALL",
        workspace=OuterRef("pk"),
    )

    # Query for dbGaPWorkspaces.
    dbgap = dbGaPWorkspace.objects.annotate(
        access_mechanism=Value("dbGaP"),
        # This query will change from workspace model to workspace model.
        is_shared=Exists(shared),
    ).values(
        "is_shared",
        "access_mechanism",
        # Rename columns to have similar names.
        workspace_name=F("workspace__name"),
        study=F("dbgap_study_accession__studies__short_name"),
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
        # Rename columns to have similar names.
        workspace_name=F("workspace__name"),
        study=F("studies__short_name"),
        data=F("available_data__name"),
    )
    df_open = pd.DataFrame.from_dict(open)

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
    df = pd.concat([df_dbgap, df_open])

    # If there are no workspaces, return an empty list.
    if df.empty:
        return []

    # Sort by specific columns
    df = df.sort_values(by=["study", "access_mechanism"])
    # Concatenate multiple studies into a single comma-delimited string.
    df = (
        df.groupby(
            ["workspace_name", "data", "is_shared", "access_mechanism"],
            dropna=False,
        )["study"]
        .apply(lambda x: ", ".join(x))
        .reset_index()
        .drop("workspace_name", axis=1)
    )
    # Replace NaNs with a dummy column for pivoting.
    df["data"] = df["data"].fillna("no_data")
    # Pivot so that the available data types are their own columns.
    data = (
        pd.pivot_table(
            df,
            index=["study", "is_shared", "access_mechanism"],
            columns=["data"],
            # set this to len to count the number of workspaces instead of returning a boolean value.
            aggfunc=lambda x: len(x) > 0,
            fill_value=False,
            # aggfunc=len,
            # fill_value=0,
            #            dropna=False,
        )
        .rename_axis(columns=None)
        .reset_index()
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
