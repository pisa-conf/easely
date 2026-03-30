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

import pandas as pd
import requests

from .logging_ import logger
from .paths import sanitize_file_path, sanitize_folder_path
from .program import PosterCollectionBase, DATETIME_FORMAT
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

    def download_attachments(self, folder_path: PathLike, separator: str = '-',
            file_types: tuple = None, overwrite: bool = False) -> int:
        """Download the attachments for this contribution, if any.

        Since downloading a bunch of files for many contribution is an expensive
        process, we provide a minimal mechanism to avoid downloading the same file
        over and over again. More specifically, the metadata that come with the .json
        file from indico include a timestamp for each attachment, which is updated
        whenever the file is uploaded or modified, and we create a small text file with
        the timestamp next to each file that we download so that we can check if the
        file is up to date before downloading it again.

        Arguments
        ---------
        folder_path : PathLike
            The path to the folder where to save the attachments.

        separator : str
            The separator to use between the contribution id and the original file name
            when saving the attachments.

        file_types : tuple
            The file types to download (None to download all attachments).

        overwrite : bool
            Whether to overwrite the files if they already exist and are up to date.

        Returns
        -------
        int
            The number of attachments downloaded.
        """
        folder_path = sanitize_folder_path(folder_path, create=True)
        num_downloads = 0
        for url, timestamp in zip(self.attachment_urls, self.attachment_timestamps):
            # Check if the file type matches the specified file types, if any.
            if file_types is not None and not url.endswith(file_types):
                logger.debug(f"{url} does not match the specified file types, skipping...")
                continue
            file_name = f"{self.friendly_id:04d}{separator}{url.split('/')[-1]}"
            file_path = folder_path / file_name
            timestamp_file_path = file_path.with_suffix(".tstamp")
            # If we have the file locally, and we have track of the timestamp, and that
            # matches the one in the .json file, there is no point in downloading another
            # identical copy.
            if file_path.is_file() and timestamp_file_path.is_file() and not overwrite:
                if timestamp_file_path.read_text() == timestamp:
                    logger.debug(f"{file_path} is up to date, skipping...")
                    continue
            # Otherwise we can go ahead and download the file.
            logger.info(f"Downloading {url} -> {file_path}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(file_path, "wb") as output_file:
                output_file.write(response.content)
            num_downloads += 1
            # And, of course, we need to write the timestamp, as well.
            logger.debug(f"Writing timestamp file to {timestamp_file_path}...")
            with open(timestamp_file_path, "w") as timestamp_file:
                timestamp_file.write(timestamp)
        return num_downloads


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

    Note the `session` field is a dictionary containing some relevant information:

    * `folders`
    * `startDate`
    * `endDate`
    * `_type`
    * `sessionConveners`
    * `title`
    * `color`
    * `textColor`
    * `description`
    * `material`
    * `isPoster`
    * `type`
    * `url`
    * `roomFullname`
    * `location`
    * `address`
    * `_fossil`
    * `numSlots`
    * `id`
    * `db_id`
    * `friendly_id`
    * `room`
    * `code`
    """

    id: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    title: str
    url: str
    is_poster: bool
    contributions: List[Contribution] = field(default_factory=list)

    @classmethod
    def from_json_dict(cls, data: dict):
        """Implementation of the AbstractIndicoObject abstract method.
        """
        args = data["id"], cls.parse_date(data["startDate"]), cls.parse_date(data["endDate"]), \
            data["title"], data["url"], data["session"]["isPoster"]
        session = cls(*args)
        # Populate the contributions from the contributions field, if any.
        for contribution_data in data["contributions"]:
            contribution = Contribution.from_json_dict(contribution_data)
            session.contributions.append(contribution)
        return session

    def __len__(self) -> int:
        """Return the number of contributions in the session.
        """
        return len(self.contributions)


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
        self.session_dict = {}
        for session_data in data["results"][0]["sessions"]:
            session = Session.from_json_dict(session_data)
            self.session_dict[session.id] = session
        logger.info(f"{len(self.session_dict)} session(s) found.")

    def poster_sessions(self, remove_empty: bool = True) -> List[Session]:
        """Return the list of poster sessions in the event, and by default remove
        those with no contributions.

        Arguments
        ---------
        remove_empty : bool
            Whether to remove the sessions with no contributions from the list (default True).

        Returns
        -------
        List[Session]
            The list of poster sessions in the event.
        """
        sessions = [session for session in self.session_dict.values() if session.is_poster]
        if remove_empty:
            sessions = [session for session in sessions if len(session) > 0]
        return sessions

    def generate_poster_roster(self, file_path: PathLike, overwrite: bool = False) -> None:
        """Generate the .xls file with the poster roster, i.e., the file that
        is consumed by the GUI elements for the actual display.

        Arguments
        ---------
        file_path : PathLike
            The path to the output .xls file.
        """
        logger.info(f"Writing poster roster to {file_path}...")
        writer = pd.ExcelWriter(file_path, engine="xlsxwriter")
        sessions = self.poster_sessions()

        # Write the program sheet with the session data.
        sheet_name = PosterCollectionBase.PROGRAM_SHEET_NAME
        col_names = PosterCollectionBase.PROGRAM_COL_NAMES
        _id = [session.id for session in sessions]
        _title = [session.title for session in sessions]
        _start_date = [session.start_date for session in sessions]
        _end_date = [session.end_date for session in sessions]
        data = _id, _title, _start_date, _end_date
        df = pd.DataFrame({key: val for key, val in zip(col_names, data)})
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        sheet = writer.sheets[sheet_name]
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 100)
        sheet.set_column(2, 3, 20)

        # Create the ancillary sheets with the actual contributions.
        # def _warning_message(msg, contribution, max_title_length=30):
        #     """Small nested function to provide useful diagnostics in case of missing data.
        #     """
        #     logger.warning(f"{msg} for contribution {contribution['id']} ({contribution['title'][:max_title_length]}...)")

        # # Loop over all the contributions in the session and retrieve the data.
        # # Note that, rather than doing this by column, we do it by row (i.e., by
        # # contribution), the basic idea being that we can provide more granular
        # # diagnostics if data are missing, at the expense of code beauty.
        # for session in self.values():
        #     data = [[], [], [], [], [], []]
        #     for contrib in session["contributions"]:
        #         _id = contrib["id"]
        #         _title = contrib["title"]
        #         _url = contrib["url"]
        #         _db_id = contrib["db_id"]
        #         try:
        #             first_speaker = contrib["speakers"][0]
        #         except IndexError as e:
        #             _warning_message("No speaker(s)", contrib)
        #             first_speaker = None
        #         if first_speaker is not None:
        #             _first_name = first_speaker["first_name"]
        #             _last_name = first_speaker["last_name"]
        #             _affiliation = first_speaker["affiliation"]
        #             if _first_name == "":
        #                 _warning_message("No first name", contrib)
        #             if _last_name == "":
        #                 _warning_message("No last name", contrib)
        #             if _affiliation == "":
        #                 _warning_message("No affiliation", contrib)
        #         else:
        #             _first_name, _last_name, _affiliation = "N/A", "N/A", "N/A"
        #         for col, val in zip(data, (_id, _db_id, _title, _first_name, _last_name, _affiliation)):
        #             col.append(val)

        #     # Placeholder for the screen id.
        #     screen_id = [i % 20 + 1 for i in range(len(session["contributions"]))]
        #     data.insert(2, screen_id)
        #     df = pd.DataFrame({key: val for key, val in zip(PosterCollectionBase.SESSION_COL_NAMES, data)})
        #     sheet_name = str(session["id"])
        #     df.to_excel(writer, sheet_name=sheet_name, index=False)
        #     sheet = writer.sheets[sheet_name]
        #     sheet.set_column(0, 2, 12)
        #     sheet.set_column(3, 3, 100)
        #     sheet.set_column(4, 5, 20)
        #     sheet.set_column(6, 6, 60)
        logger.info("Writing output file...")
        writer.close()
        logger.info("Done.")

    def download_poster_attachments(self, folder_path: PathLike, file_types: tuple = None,
            overwrite: bool = False) -> int:
        """Download the attachments for all the poster sessions in the event.

        Arguments
        ---------
        folder_path : PathLike
            The path to the folder where to save the attachments.

        file_types : tuple
            The file types to download (None to download all attachments).

        overwrite : bool
            Whether to overwrite the files if they already exist and are up to date.

        Returns
        -------
        int
            The number of attachments downloaded.
        """
        logger.info(f"Downloading attachments for all poster sessions in the event...")
        kwargs = dict(folder_path=folder_path, file_types=file_types, overwrite=overwrite)
        num_downloads = 0
        for session in self.poster_sessions():
            logger.info(f"Downloading attachments for session {session.id}: {session.title}...")
            for contribution in session.contributions:
                num_downloads += contribution.download_attachments(**kwargs)
        logger.info(f"Done, {num_downloads} file(s) downloaded.")
        return num_downloads

    def generate_poster_qrcodes(self, folder_path: PathLike) -> None:
        """
        """
        logger.info(f"Generating QR codes for all poster sessions in the event...")