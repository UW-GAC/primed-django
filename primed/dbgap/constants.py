json_dar_schema = {
    "title": "dbGaP DAR schema",
    "description": "json schema for the dbGaP DAR data",
    "type": "array",
    "items": {"$ref": "#/$defs/project"},
    "minItems": 1,
    "maxItems": 1,
    "$defs": {
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
    },
}
