from urllib.parse import urlencode


def get_dbgap_dar_json_url(project_ids):
    """Return the dbGaP URL that lists DARs for this application."""
    if not isinstance(project_ids, list):
        project_ids = [project_ids]

    url_params = {
        "name": "project_report",
        "page": "getreport",
        "mode": "json",
        "filter": ["mode", "project_list"],
        "project_list": ",".join([str(x) for x in project_ids]),
    }
    url = "https://dbgap.ncbi.nlm.nih.gov/aa/wga.cgi?%s"
    # Doseq means to generate the filter key twice, once for "mode" and once for "project_list"
    return url % urlencode(url_params, doseq=True)
