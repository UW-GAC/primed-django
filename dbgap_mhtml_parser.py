import argparse
import json
import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup, Tag
from mhtml_converter import convert_mhtml


@dataclass
class dbGaPDAR:
    id: int
    dac: str
    full_consent: str
    consent_code: int
    current_version: int
    current_status: str
    raw_html: Tag = None

    def _get_consent_abbreviation(self, consent_map):
        try:
            this_code = consent_map[self.consent_code]
        except KeyError:
            print(f"Could not find consent code {self.consent_code} in consent map for DAR {self.id}")
            raise
        # Check that the full string matches, ignoring case.
        name_consent_group = this_code.get("name_consent_group")
        name_participant_set = this_code.get("name_participant_set")
        if name_consent_group and self.full_consent.lower() == name_consent_group.lower():
            pass
        elif name_participant_set and self.full_consent.lower() == name_participant_set.lower():
            pass
        else:
            # Sometimes the string has the consent abbreviation in parentheses. Check that next.
            full_consent_with_code = f"{self.full_consent} ({this_code.get('short_name')})"
            if name_consent_group and full_consent_with_code.lower() == name_consent_group.lower():
                pass
            elif name_participant_set and full_consent_with_code.lower() == name_participant_set.lower():
                pass
            else:
                raise ValueError(f"Consent string mismatch for code {self.consent_code} (DAR {self.id})")
        return this_code.get("short_name")

    def get_json(self, consent_map):
        return {
            "DAC_abbrev": self.dac,
            "consent_abbrev": self._get_consent_abbreviation(consent_map),
            "consent_code": self.consent_code,
            "DAR": self.id,
            "current_version": self.current_version,
            "current_DAR_status": self.current_status,
            "was_approved": "unknown",
        }


@dataclass
class dbGaPStudy:
    phs: int
    name: str
    version: int
    participant_set: int
    dars: list[dbGaPDAR] = field(default_factory=list)
    consent_code_map: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.consent_code_map = self._get_consent_code_map()

    def _get_consent_code_map(self):
        # First, check if we've hardcoded any overrides.
        map = self._get_consent_code_map_hardcoded()
        # Parsing the XML is faster, so we'll try that first.
        if not map:
            try:
                map = self._get_consent_code_map_from_xml()
            except requests.HTTPError:
                map = self._get_consent_code_map_from_api()
        return map

    def _get_consent_code_map_hardcoded(self):
        # A place we can hard-code consent code mappings if needed.
        return None

    def _get_consent_code_map_from_api(self):
        url = f"https://www.ncbi.nlm.nih.gov/gap/sstr/api/v1/study/phs{self.phs:06d}.v{self.version}/summary"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()["study"]["consent_groups"]

    def _get_consent_code_map_from_xml(self):
        full_accession_string = f"phs{self.phs:06d}.v{self.version}.p{self.participant_set}"
        url = f"https://ftp.ncbi.nlm.nih.gov/dbgap/studies/phs{self.phs:06d}/{full_accession_string}/GapExchange_{full_accession_string}.xml"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "xml")
        consent_map = {}
        # First look at the ConsentGroup elements.
        consent_group_elements = soup.find_all("ConsentGroup")
        for x in consent_group_elements:
            consent_map[int(x.attrs.get("groupNum"))] = {
                "name_consent_group": x.attrs.get("longName"),
                "name_participant_set": None,
                "short_name": x.attrs.get("shortName"),
            }

        # THen look at the ParticipantSet elements, and add those that don't exist.
        consent_group_elements = soup.find_all("ParticipantSet")
        for x in consent_group_elements:
            try:
                mapping = consent_map[int(x.attrs.get("groupNum-REF"))]
            except KeyError:
                # Add the new code
                consent_map[int(x.attrs.get("groupNum-REF"))] = {
                    "name_consent_group": None,
                    "name_participant_set": x.find("ConsentName").text,
                    "short_name": x.find("ConsentAbbrev").text,
                }
            else:
                # Make sure the code matches.
                assert mapping["short_name"] == x.find("ConsentAbbrev").text
                # Store the full string for this consent group.
                mapping["name_participant_set"] = x.find("ConsentName").text

        return consent_map

    def get_json(self):
        return {
            "study_name": self.name,
            "study_accession": f"phs{self.phs:06d}",
            "requests": [x.get_json(self.consent_code_map) for x in self.dars],
        }


@dataclass
class dbGaPApplication:
    mhtml_file: str

    pi_name: str = None
    project_id: int = None
    project_closed: str = None
    studies: dict[str, dbGaPStudy] = field(default_factory=dict)
    html: str = None
    verbose: bool = True
    html_table: BeautifulSoup = None
    html_table_index_dar_id: int = None
    html_table_index_dar_status: int = None
    html_table_index_study_consent: int = None

    def __post_init__(self):
        self.html = self._convert_mhtml()
        self.pi_name = self._get_pi_name()
        self.project_id = self._get_project_id()

    def __str__(self):
        return f"dbGaPApplication ID={self.project_id}, PI={self.pi_name} ({self.mhtml_file})"

    def __repr__(self):
        return self.__str__()

    def _convert_mhtml(self):
        """Convert the mhtml file to html and return a BeautifulSoup object."""
        html_content = convert_mhtml(self.mhtml_file)
        return BeautifulSoup(html_content, "html.parser")

    def _get_pi_name(self):
        """Extract the PI name from the html."""
        x = self.html(text=re.compile("Principal Investigator's"))
        assert len(x) == 1
        if self.verbose:
            print(f"Found PI name element: {x[0].parent.parent.text}")
        return x[0].parent.parent.text.replace("\xa0", " ").split(": ")[1].strip()

    def _get_project_id(self):
        """Extract the project ID from the html."""
        elements = self.html.find_all("h2")
        assert len(elements) == 1
        if self.verbose:
            print(f"Found project id element: {elements[0].text}")
        pattern = r"#(\d{5}):"
        match = re.search(pattern, elements[0].text)
        if match is None:
            raise ValueError("Could not parse project id from html")
        return int(match.group(1))

    def _parse_study_consent_string(self, study_consent_element):
        """Parse the "Study, Consent" field from the DAR table and extract relevant information.

        Args:
            study_consent_string (str): The string from the "Study, Consent" field in the DAR table.

        Returns: A re.match object with the following groups:
            - study_name
            - phs
            - phs_version
            - phs_participant_set
            - phs_consent_code
            - dac
        """
        study_consent_string = study_consent_element.text.strip().replace("\xa0", " ")
        pattern = r"(?P<study_name>.+?)\n +\(phs\d{6}\.v\d{1,}\.p\d{1,}\)\n +\n(?P<consent_string>.+)\n.+\(phs(?P<phs>\d{6})\.v(?P<phs_version>\d{1,})\.p(?P<phs_participant_set>\d{1,})\.c(?P<phs_consent_code>\d{1,})\)\, (?P<dac>.+)"  # noqa: E501
        match = re.search(pattern, study_consent_string)
        if match is None:
            raise ValueError(f"Could not parse Study, Consent field: {study_consent_string}")
        d = match.groupdict()
        d["phs"] = int(d["phs"])
        d["phs_version"] = int(d["phs_version"])
        d["phs_participant_set"] = int(d["phs_participant_set"])
        d["phs_consent_code"] = int(d["phs_consent_code"])
        d["consent_string"] = d["consent_string"].strip()
        d["dac"] = d["dac"].strip()
        return d

    def _get_or_add_dbgap_study(self, phs, study_name, version, participant_set):
        """Get an existing study or create a new one."""
        phs_string = f"phs{phs:06d}"
        try:
            dbgap_study = self.studies[phs_string]
        except KeyError:
            dbgap_study = dbGaPStudy(phs=phs, name=study_name, version=version, participant_set=participant_set)
            self.studies[phs_string] = dbgap_study
            if self.verbose:
                print(f"- {phs_string}: created new study for {study_name}")
        else:
            # If the record exists, check that the information has not changed.
            if dbgap_study.name != study_name:
                raise ValueError(f"Study name mismatch for {phs_string}: {dbgap_study.name} != {study_name}")
            if dbgap_study.version != version:
                raise ValueError(f"Study version mismatch for {phs_string}: {dbgap_study.version} != {version}")
            if dbgap_study.participant_set != participant_set:
                raise ValueError(
                    f"Participant set mismatch for {phs_string}: {dbgap_study.participant_set} != {participant_set}"
                )
        return dbgap_study

    def _get_dar_status(self, status_element):
        # First, parse out the class of the status element.
        x = status_element.find_all("span", {"class": "status"})
        assert len(x) == 1
        # Parse out the classes and the text of the status element, and use those to determine the DAR status.
        status_text = [y.strip().lower() for y in x[0].text.split("\n")]
        status_text = set([y for y in status_text if len(y) > 0])
        status_classes = x[0].attrs.get("class")
        status_classes.remove("status")
        status_classes = set(status_classes)

        if self.verbose:
            print("    - html:")
            print("      - status text:", status_text)
            print("      - status classes:", status_classes)

        if status_classes == set(["approved"]) and status_text == set(["approved", "granted"]):
            status = "approved"
        elif status_classes == set(["rejected"]) and status_text == set(["rejected"]):
            status = "rejected"
        elif status_classes == set() and status_text == set(["closed"]):
            status = "closed"
        elif status_classes == set(["revision_requested"]) and status_text == set(["rev. requested", "expired"]):
            status = "expired"
        elif status_classes == set(["revision_requested"]) and status_text == set(["rev. requested"]):
            status = "new"
        elif status_classes == set(["staff_queued"]) and status_text == set(["dac review", "granted"]):
            status = "approved"
        else:
            raise (ValueError("Unknown DAR status"))

        if self.verbose:
            print(f"    - parsed DAR status: {status}")
        return status

    def _set_html_table_indices(self):
        table_header = self.html_table.find("thead").find_all("th")
        header = [x.text.lower().strip() for x in table_header]

        self.html_table_index_dar_id = header.index("dar #")
        self.html_table_index_dar_status = header.index("status")
        self.html_table_index_study_consent = header.index("study, consent")

    def _add_dar(self, table_row):
        """Add a DAR to the application based on the row of the HTML DAR table.

        Args:
            table_row (bs4.element.Tag): A BeautifulSoup tag representing a row in the DAR table.
        """

        table_columns = table_row.find_all("td")

        # Parse out specific information from the "Study, Consent" field
        # groups: study_name, phs, phs_version, phs_participant_set_version, phs_consent_code, dac
        matches = self._parse_study_consent_string(table_columns[self.html_table_index_study_consent])

        # If needed, add the associated accession to the application.
        dbgap_study = self._get_or_add_dbgap_study(
            phs=matches["phs"],
            study_name=matches["study_name"],
            version=matches["phs_version"],
            participant_set=matches["phs_participant_set"],
        )

        # Get the DAR identifier and version.
        dar_id_and_version = table_columns[self.html_table_index_dar_id].text.strip()
        dar_id = dar_id_and_version.split("-")[0]
        dar_version = dar_id_and_version.split("-")[1]

        if self.verbose:
            print(f"  - DAR {dar_id}")

        # Get the status of this DAR.
        dar_status = self._get_dar_status(table_columns[self.html_table_index_dar_status])

        # Now add the DAR to this study.
        this_dar = dbGaPDAR(
            id=int(dar_id),
            dac=matches["dac"],
            full_consent=matches["consent_string"],
            consent_code=matches["phs_consent_code"],
            current_version=int(dar_version),
            current_status=dar_status,
            raw_html=table_row,
        )
        dbgap_study.dars.append(this_dar)

    def populate_studies_and_dars(self, n_dars=None, phs=None):
        """Populate the studies and dars for this application by parsing the DAR table in the HTML."""
        if self.verbose:
            print("Populating studies and DARs...")

        # First, get the table with DAR information. It should be the only table on the page.
        tables = self.html.find_all("table")
        assert len(tables) == 1
        self.html_table = tables[0]

        # Set the indices where we will look for specific information in the table rows.
        self._set_html_table_indices()

        # Each row in the table body represents a single DAR.
        table_rows = self.html_table.find("tbody").find_all("tr")
        if phs:
            table_rows = [x for x in table_rows if f"(phs{int(phs):06d}." in x.text]
            if self.verbose:
                print(f"Filtered DARs to only those for phs{int(phs):06d}, {len(table_rows)} DARs remain.")
        for i, row in enumerate(table_rows):
            if i == n_dars:
                if self.verbose:
                    print(f"Reached n_dars={n_dars}, stopping parsing of DARs.")
                break
            self._add_dar(row)

    def get_json(self):
        return [
            {
                "Project_id": self.project_id,
                "PI_name": self.pi_name,
                "Project_closed": "unknown",
                "studies": [x.get_json() for x in self.studies.values()],
            }
        ]

    def write_json(self, output_file):
        """Write the application information to a json file."""
        with open(output_file, "w") as json_file:
            json.dump(self.get_json(), json_file, indent=4)

    def write_html(self, output_file):
        """Write the application information to an html file."""
        with open(output_file, "w") as html_file:
            html_file.write(self.html.prettify())


if __name__ == "__main__":
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Parse DAR info from an mhtml file.")
    parser.add_argument("--mhtml", type=str, help="Path to the mhtml file to parse.")
    parser.add_argument("--output-json", type=str, help="Path to the output json file.")
    parser.add_argument(
        "--output-html",
        type=str,
        help="Path to the output html file. If None, no file will be written.",
        default=None,
    )
    parser.add_argument("--n-dars", type=int, default=None, help="Number of DARs to populate for; None means all DARs.")
    parser.add_argument(
        "--phs", type=int, default=None, help="Only parse DARs for this PHS accession (e.g. 93 for phs000093)."
    )
    args = parser.parse_args()

    application = dbGaPApplication(args.mhtml)
    if args.output_html:
        application.write_html(args.output_html)

    application.populate_studies_and_dars(n_dars=args.n_dars, phs=args.phs)
    application.write_json(args.output_json)
