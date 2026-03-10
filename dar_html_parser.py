import argparse
import re
from dataclasses import dataclass, field

# import json
# import requests
from bs4 import BeautifulSoup
from mhtml_converter import convert_mhtml


@dataclass
class dbGaPDAR:
    id: int
    dac: str
    full_consent: str
    consent_abbreviation: str
    consent_code: int
    current_version: int
    current_status: str


@dataclass
class dbGaPStudy:
    phs: int
    name: str
    version: int
    participant_set: int
    dars: list[dbGaPDAR] = field(default_factory=list)


@dataclass
class dbGaPApplication:
    mhtml_file: str

    pi_name: str = None
    project_id: int = None
    project_closed: str = None
    studies: list[dbGaPStudy] = field(default_factory=list)
    html: str = None
    verbose: bool = True

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

    def add_dar(self, table_row_dict):
        """Add a DAR to the application based on a dict of values from the HTML table.

        Args:
            table_row_dict (dict): A dict containing the values from a row of the DAR table in the HTML.
        """


if __name__ == "__main__":
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Parse DAR info from an mhtml file.")
    parser.add_argument("--mhtml", type=str, help="Path to the mhtml file to parse.")
    parser.add_argument("--output", type=str, help="Path to the output json file.")
    args = parser.parse_args()

    application = dbGaPApplication(args.mhtml)

# def parse_html(mhtml_file):
#     html_content = convert_mhtml(mhtml_file)
#     return BeautifulSoup(html_content, "html.parser")


# def get_consent_mapping_for_study(phs, version):
#     url = "https://www.ncbi.nlm.nih.gov/gap/sstr/api/v1/study/phs{:06.0f}.v{}/summary".format(phs, version)
#     response = requests.get(url)
#     mapping = response.json()["study"]["consent_groups"]
#     return mapping


# def get_dar_list_from_html(soup):

#     # Get the table with DAR info.
#     table = soup.find("table")
#     table_header = table.find("thead").find_all("th")
#     table_rows = table.find("tbody").find_all("tr")

#     # Get the column names in a readable format, ignore HTML attributes and whitespace.
#     keys = [x.text.strip() for x in table_header]

#     phs_dac_pattern = r"\((phs\d{6})\.v(\d+?).p(\d+?).c(\d+?)\), (.+)"

#     # Now loop over the table rows and create a list of dicts.
#     data = []
#     for row in table_rows:
#         row_dict = {}
#         tds = [x.text.strip() for x in row.find_all("td")]
#         for i, td in enumerate(tds):
#             # Replace non-breaking space with regular space.
#             # Replace newlines with semicolons
#             row_dict[keys[i]] = td.replace("\xa0", " ")  # .replace("\n", ";")
#         # Now parse out more specific information from the "Study, Consent" field.
#         tmp = [x.strip() for x in row_dict["Study, Consent"].split("\n")]
#         d = {}
#         d["study_name"] = tmp[0]
#         d["consent_string"] = tmp[3]
#         # Now try regex matching...
#         match = re.match(phs_dac_pattern, tmp[4])
#         if match is None:
#             raise ValueError(f"Could not parse row: {row}")
#         d["phs"] = match.group(1)
#         d["phs_version"] = int(match.group(2))
#         d["phs_participant_set_version"] = int(match.group(3))
#         d["phs_consent_code"] = int(match.group(4))
#         d["dac"] = match.group(5)
#         # Now split the DAR string into the id and the version.
#         tmp = row_dict["DAR #"].split("-")
#         assert len(tmp) == 2
#         d["dar_id"] = int(tmp[0])
#         d["dar_version"] = int(tmp[1])
#         row_dict.update(d)
#         data.append(row_dict)

#     return data


# def reformat_dar_list_by_study(data):
#     # Now we will loop over accessions and create a new dict with the relevant DARs for that phs.
#     study_dict = {}
#     for row in data:
#         phs = row["phs"]
#         if phs not in study_dict:
#             d = {
#                 "study_name": row["study_name"],
#                 "study_accession": row["phs"],
#                 "phs_version": row["phs_version"],
#                 "requests": [],
#             }
#         else:
#             d = study_dict[phs]
#             # Verify that the study name is the same across rows with the same phs.
#             assert row["study_name"] == d["study_name"]
#             assert row["phs"] == d["study_accession"]
#         # Now add the DAR info.
#         dar_dict = {}
#         dar_dict["DAC_abbrev"] = row["dac"]
#         dar_dict["consent_string"] = row["consent_string"]
#         dar_dict["consent_abbrev"] = ""  # Needs to be created from consent_string, but not sure how to do that yet.
#         dar_dict["consent_code"] = row["phs_consent_code"]
#         dar_dict["DAR"] = row["dar_id"]
#         dar_dict["current_version"] = row["dar_version"]
#         # Set current DAR status.
#         if "approved" in row["Status"].lower():
#             dar_dict["current_DAR_status"] = "approved"
#         elif "expired" in row["Status"].lower():
#             dar_dict["current_DAR_status"] = "expired"
#         elif "rejected" in row["Status"].lower():
#             dar_dict["current_DAR_status"] = "rejected"
#         elif "closed" in row["Status"].lower():
#             dar_dict["current_DAR_status"] = "closed"
#         elif "new" in row["Status"].lower():
#             dar_dict["current_DAR_status"] = "new"
#         else:
#             raise ValueError(f"Unknown DAR status: {row['Status']}")
#         dar_dict["was_approved"] = "unknown"
#         d["requests"].append(dar_dict)
#         study_dict.update({phs: d})
#     # Extract the values - we don't care about the key/mapping anymore.
#     return [x for x in study_dict.values()]


# def add_consent_abbreviation(study_dict):

#     pass


# def get_project_id_from_html(soup):
#     # Get the project id.
#     elements = soup.find_all("h2")
#     assert len(elements) == 1
#     elements[0].text
#     pattern = r"#(\d{5}):"
#     match = re.search(pattern, elements[0].text)
#     if match is None:
#         raise ValueError("Could not parse project id from html")
#     project_id = int(match.group(1))
#     return project_id


# def get_pi_name_from_html(soup):
#     x = soup(text=re.compile("Principal Investigator's"))
#     assert len(x) == 1
#     pi_name = x[0].parent.parent.text.replace("\xa0", " ").split(": ")[1].strip()
#     return pi_name


# if __name__ == "__main__":
#     # Parse command line arguments.
#     parser = argparse.ArgumentParser(description="Parse DAR info from an mhtml file.")
#     parser.add_argument("--mhtml", type=str, help="Path to the mhtml file to parse.")
#     parser.add_argument("--output", type=str, help="Path to the output json file.")
#     args = parser.parse_args()

#     # Convert the mhtml and read the converting html.
#     mhtml_file = args.mhtml
#     soup = parse_html(mhtml_file)

#     # Extract and process DARs to match the expected json format.
#     dars = get_dar_list_from_html(soup)
#     dars_by_study = reformat_dar_list_by_study(dars)
#     dars_by_study_with_consent_abbreviation = add_consent_abbreviation(dars_by_study)

#     # Extract other relevant information for creating the json.
#     pi_name = get_pi_name_from_html(soup)
#     project_id = get_project_id_from_html(soup)

#     # Finally, create the json output.
#     x = {
#         "Project_id": project_id,
#         "PI_name": pi_name,
#         "Project_closed": "unknown",
#         "studies": [x for x in dars_by_study_with_consent_abbreviation.values()],
#     }

#     # Write the json to a file.
#     output_file = args.output
#     with open(output_file, "w") as json_file:
#         json.dump(x, json_file, indent=4)
