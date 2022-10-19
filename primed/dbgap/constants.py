json_dar_defs = {
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
        "required": ["consent_abbrev", "consent_code", "DAR", "current_DAR_status"],
        "properties": {
            "consent_abbrev": {"type": "string"},
            "consent_code": {"type": "number"},
            "DAR": {"type": "number"},
            "current_DAR_status": {"type": "string"},
        },
    },
}


# Validation of dbGaP DAR JSON from their web service (a array of multiple project DARs).
json_dar_schema = {
    "title": "dbGaP DAR schema",
    "description": "json schema for the dbGaP DAR data",
    "type": "array",
    "items": {"$ref": "#/$defs/project"},
    "minItems": 1,
    "maxItems": 1,
    "$defs": json_dar_defs,
}

# Validation fo dbGaP DAR JSON for a single project (one entry in what's returned by their web servce).
json_dar_schema_one_project = {
    "title": "dbGaP Project DAR schema",
    "description": "json schema for DARs for a single dbGaP project",
    "$ref": "#/$defs/project",
    "$defs": json_dar_defs,
}
