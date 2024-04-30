DBGAP_STUDY_URL = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi"
PHS_REGEX = r"^phs(?P<phs>\d{6})$"
FULL_ACCESSION_REGEX = r"^phs(?P<phs>\d{6})\.v(?P<version>\d+?)\.p(?P<participant_set>\d+?)$"

JSON_DAR_DEFS = {
    "project": {
        "required": ["Project_id", "studies"],
        "type": "object",
        "properties": {
            "Project_id": {
                "description": "dbGaP-assigned unique identifier for this application.",
                "type": "number",
            },
            "PI_name": {
                "description": "Name of the principal investigator.",
                "type": "string",
            },
            "Project_closed": {
                "description": "Is the project closed?",
                "type": "string",
            },
            "studies": {"type": "array", "items": {"$ref": "#/$defs/study"}},
        },
    },
    "study": {
        "required": ["study_accession", "requests"],
        "type": "object",
        "properties": {
            "study_name": {"type": "string"},
            "study_accession": {"type": "string"},
            "requests": {"type": "array", "items": {"$ref": "#/$defs/request"}},
        },
    },
    "request": {
        "type": "object",
        "required": [
            "consent_abbrev",
            "consent_code",
            "DAR",
            "current_DAR_status",
            "DAC_abbrev",
        ],
        "properties": {
            "consent_abbrev": {"type": "string"},
            "consent_code": {"type": "number"},
            "DAR": {"type": "number"},
            "current_DAR_status": {"type": "string"},
            "DAC_abbrev": {"type": "string"},
        },
    },
}


# Validation of dbGaP DAR JSON from their web service (a array of multiple project DARs).
JSON_DAR_SCHEMA = {
    "title": "dbGaP DAR schema",
    "description": "json schema for the dbGaP DAR data, allowing multiple projects.",
    "type": "array",
    "items": {"$ref": "#/$defs/project"},
    "minItems": 1,
    "$defs": JSON_DAR_DEFS,
}

# Validation fo dbGaP DAR JSON for a single project (one entry in what's returned by their web servce).
JSON_PROJECT_DAR_SCHEMA = {
    "title": "dbGaP Project DAR schema",
    "description": "json schema for DARs for a single dbGaP project",
    "$ref": "#/$defs/project",
    "$defs": JSON_DAR_DEFS,
}
