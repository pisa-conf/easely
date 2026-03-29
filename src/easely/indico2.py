# Copyright (C) 2022--2026, the easely team.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""INDICO interface.
"""

import datetime
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import requests

from .logging_ import logger
from .paths import sanitize_file_path
from .typing_ import PathLike

_DATE_FORMAT = "%Y-%m-%d"
_TIME_FORMAT = "%H:%M:%S"
_DATETIME_FORMAT = f"{_DATE_FORMAT} {_TIME_FORMAT}"


def download_event_data(url: str, file_path: PathLike, detail: str = "sessions",
                        overwrite: bool = True):
    """Download all the event data from indico and save it to a .json file.

    Retrieve the contributions, grouped by session for a given conference,
    following the instructions at
    https://docs.getindico.io/en/stable/http-api/exporters/event/#sessions

    According to the documentation, this setting details to "sessions" includes
    details about the different sessions and groups contributions by sessions.
    The top-level contributions list only contains contributions which are not
    assigned to any session. Sub-contributions are included in this details level,
    too.

    Arguments
    ---------
    url : str
        The indico url for the conference, e.g., https://agenda.infn.it/export/event/8397.json

    file_path : PathLike
        The path for the output .json file

    detail : str
        The level of detail for the dump, see
        https://docs.getindico.io/en/stable/http-api/exporters/event

    overwrite : bool
        Overwrite the output file.

    Returns
    -------
    pathlib.Path
        The path to the output .json file.
    """
    file_path = sanitize_file_path(file_path, suffix=".json", check_exists=False)
    if file_path.exists() and overwrite is False:
        print(f"File {file_path} exists, skipping (delete it or set overwrite=True)...")
        return file_path
    logger.info(f"Retrieving event data from {url}...")
    resp = requests.get(f"{url}?detail={detail}&pretty=yes")
    data = resp.json()
    with open(file_path, "w") as output_file:
        json.dump(data, output_file, indent=4)
    logger.info(f"Event data saved to {file_path}...")
    return file_path


class AbstractIndicoObject(ABC):

    """Abstract class to represent an indico object, as retrieved from the indico API.

    This defines a single abstract method, `from_json_dict`, to create an indico object
    from a fragment of the .json file retrieved from the indico API, as a Python dictionary.
    """

    @staticmethod
    def parse_date(date: dict) -> datetime.datetime:
        """Parse a date/time dictionary as retrieved from the indico API, e.g.,
        {'date': '2015-05-28', 'time': '15:45:00', 'tz': 'Europe/Rome'}.

        Arguments
        ---------
        date : dict
            The date dictionary to parse.

        Returns
        -------
        datetime.datetime
            The datetime object corresponding to the input date dictionary.
        """
        return datetime.datetime.strptime(f"{date['date']} {date['time']}", _DATETIME_FORMAT)

    @classmethod
    @abstractmethod
    def from_json_dict(cls, data: dict):
        """Create an indico object from a dictionary containing the relevant fields.

        Arguments
        ---------
        data : dict
            The dictionary containing the indico object data, as retrieved from the
            indico API.

        Returns
        -------
        AbstractIndicoObject
            The indico object created from the given data.
        """
        pass


@dataclass(frozen=True)
class Presenter(AbstractIndicoObject):

    """Class to represent the information about a presenter of an indico event, as
    retrieved from the indico API.

    The underlying .json file is parsed as a Python dictionary containing the
    following keys at the top level:

    * `_type`
    * `_fossil`
    * `first_name`
    * `last_name`
    * `fullName`
    * `affiliation`
    * `emailHash`
    * `db_id`
    * `person_id`
    """

    first_name: str = "N/A"
    last_name: str = "N/A"
    affiliation: str = "N/A"

    @classmethod
    def from_json_dict(cls, data: dict):
        """Implementation of the AbstractIndicoObject abstract method.
        """
        args = data["first_name"], data["last_name"], data["affiliation"]
        return cls(*args)


@dataclass(frozen=True)
class Contribution(AbstractIndicoObject):

    """Class to represent the information about a contribution of an indico event, as
    retrieved from the indico API.

    The underlying .json file is parsed as a Python dictionary containing the
    following keys at the top level:

    * '_type'
    * `_fossil`
    * `id`
    * `db_id`
    * `friendly_id`
    * `title`
    * `startDate`
    * `endDate`
    * `duration`
    * `roomFullname`
    * `room`
    * `note`
    * `location`
    * `type`
    * `description`
    * `folders`
    * `url`
    * `material`
    * `speakers`
    * `primaryauthors`
    * `coauthors`
    * `keywords`
    * `track`
    * `session`
    * `references`
    * `board_number`

    The `folders` field of the contribution is a list of dictionaries, each containing
    the following keys:

    * `_type`
    * `id`
    * `title`
    * `description`
    * `attachments`

    The latter, in turn, is a list of dictionaries, each one containing the following keys

    * `_type`
    * `id`
    * `download_url`
    * `title`
    * `description`
    * `modified_dt`
    * `type`
    * `is_protected`
    * `filename`
    * `content_type`
    * `size`
    * `checksum`
    """

    db_id: int
    friendly_id: int
    title: str
    presenter: Presenter
    attachment_urls: List[str] = field(default_factory=list)
    attachment_timestamps: List[str] = field(default_factory=list)

    @classmethod
    def from_json_dict(cls, data: dict):
        """Implementation of the AbstractIndicoObject abstract method.
        """
        # Need a try-except block here since some contributions do not have any speaker,
        # and the speakers field is an empty list in that case.
        try:
            presenter = Presenter.from_json_dict(data["speakers"][0])
        except IndexError:
            presenter = Presenter()
        # Create the contribution object from the relevant fields.
        args = data["db_id"], data["friendly_id"], data["title"], presenter
        contribution = cls(*args)
        # Populate the attachment urls and timestamps from the folders field, if any.
        for folder in data["folders"]:
            for attachment in folder["attachments"]:
                contribution.attachment_urls.append(attachment["download_url"])
                contribution.attachment_timestamps.append(attachment["modified_dt"])
        return contribution

    def download_attachments(self, folder_path: PathLike) -> None:
        """Download the attachments for this contribution, if any.

        """
        pass


@dataclass
class Session(AbstractIndicoObject):

    """Class to represent the information about a session of an indico event, as
    retrieved from the indico API.

    The underlying .json file is parsed as a Python dictionary containing the
    following keys at the top level:

    * `_type`
    * `_fossil`
    * `id`
    * `conference`
    * `startDate`
    * `endDate`
    * `description`
    * `title`
    * `url`
    * `contributions`
    * `note`
    * `session`
    * `room`
    * `roomFullname`
    * `location`
    * `inheritLoc`
    * `inheritRoom`
    * `slotTitle`
    * `address`
    * `conveners`
    """

    start_date: datetime.datetime
    end_date: datetime.datetime
    title: str
    url: str
    contributions: List[Contribution] = field(default_factory=list)

    @classmethod
    def from_json_dict(cls, data: dict):
        """Implementation of the AbstractIndicoObject abstract method.
        """
        args = cls.parse_date(data["startDate"]), cls.parse_date(data["endDate"]), \
            data["title"], data["url"]
        session = cls(*args)
        # Populate the contributions from the contributions field, if any.
        for contribution_data in data["contributions"]:
            contribution = Contribution.from_json_dict(contribution_data)
            session.contributions.append(contribution)
        return session


class Event:

    """Class to represent the information about an indico event, as retrieved from
    the indico API.

    The underlying .json file is parsed as a Python dictionary containing the
    following keys at the top level:

    * `count`
    * `additionalInfo`
    * `ts`
    * `url`
    * `results`
    * `_type`

    We assume that `count = 1` reflecting the length of the `results` field, which
    is a list whose first element contains the actual data.

    Now, `results[0]` is another dictionary whose keys are:

    * `_type`
    * `id`
    * `title`
    * `description`
    * `startDate`
    * `timezone`
    * `endDate`
    * `room`
    * `location`
    * `address`
    * `type`
    * `references`
    * `_fossil`
    * `categoryId`
    * `category`
    * `note`
    * `roomFullname`
    * `url`
    * `creationDate`
    * `creator`
    * `hasAnyProtection`
    * `roomMapURL`
    * `folders`
    * `chairs`
    * `material`
    * `keywords`
    * `visibility`
    * `contributions`
    * `sessions`

    The last two are the relevant pieces of information, containing the sessions,
    as well as the orphan contributions, if any.

    Arguments
    ---------
    file_path : PathLike
        The path to the .json file containing the event data, as retrieved from
        the indico API.
    """

    def __init__(self, file_path: PathLike):
        """Initialize the Event object by loading the data from the given .json file.
        """
        file_path = sanitize_file_path(file_path, suffix=".json", check_exists=True)
        logger.info(f"Reading event data from {file_path}...")
        with open(file_path) as input_file:
            data = json.load(input_file)
        if data["count"] != 1:
            raise RuntimeError(f"Expected count=1 in {file_path}, got {data['count']}")
        self.url = data["url"]
        sessions = data["results"][0]["sessions"]
        logger.info(f"{len(sessions)} session(s) found.")
        for data in sessions:
            session = Session.from_json_dict(data)
            print(session)