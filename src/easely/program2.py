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

"""Basic description of the conference program.
"""

import random
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from . import schema
from .logging_ import logger
from .paths import WorkspaceLayout, sanitize_file_path
from .typing_ import PathLike


def _trim_string(string: str, max_chars: int) -> str:
    """Return a shortened version of the string, trimmed to a fixed maximum
    number of characters if too long.

    Arguments
    ---------
    string : str
        The string to shorten.

    max_chars : int
        The maximum number of characters to keep in the shortened string.

    Returns
    -------
    shortened_string : str
        The shortened version of the string, with "..." appended if it was trimmed.
    """
    if len(string) <= max_chars:
        return string.ljust(max_chars)
    return f'{string[:max_chars - 3]}...'


@dataclass(frozen=True)
class Presenter:

    """Presenter descriptor.

    Arguments
    ---------
    first_name : str
        The presenter first name (including middle name initials where appropriate).

    last_name : str
        The presenter last name.

    affiliation : str
        The presenter affiliation.
    """

    first_name: str
    last_name: str
    affiliation: str

    def full_name(self) -> str:
        """Return the presenter full name.
        """
        return f'{self.first_name} {self.last_name}'

    def short_affiliation(self, max_chars: int = 25) -> str:
        """Return a shortened version of the affiliation.
        """
        return _trim_string(self.affiliation, max_chars)

    def __str__(self) -> str:
        """String formatting.
        """
        return f'{self.full_name()} ({self.affiliation})'


@dataclass
class Poster:

    """Poster contribution descriptor.

    Arguments
    ---------
    friendly_id : int
        The unique identifier of the contribution in indico.

    screen_id : int
        The identifier of the screen the contribution needs to be projected on.

    title : str
        The contribution title.

    presenter : Presenter instance
        The contribution presenter.
    """

    friendly_id: int
    screen_id: int
    title: str
    presenter: Presenter

    @classmethod
    def from_dataframe_row(cls, row: pd.core.series.Series) -> "Poster":
        """Create a Poster object from a dataframe row.
        """
        return cls(*row[:-3], Presenter(*row[-3:]))

    def short_title(self, max_chars: int = 40):
        """Return a shortened version of the title, trimmed to a fixed maximum
        number of characters if too long.
        """
        return _trim_string(self.title, max_chars)


@dataclass
class Session:

    """Session descriptor.
    """

    id: int
    title: str
    start_datetime: datetime
    end_datetime: datetime
    posters: list[Poster] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization processing.
        """
        self.start_datetime = Program.parse_datetime(self.start_datetime)
        self.end_datetime = Program.parse_datetime(self.end_datetime)

    @classmethod
    def from_dataframe_row(cls, row: pd.core.series.Series) -> "Session":
        """Create a Session object from a dataframe row.
        """
        return cls(*row)

    def add(self, poster: Poster) -> None:
        """Add a poster to the session.
        """
        self.posters.append(poster)

    def __len__(self) -> int:
        """Return the number of posters in the session.
        """
        return len(self.posters)


class Program:

    """Conference program descriptor.

    Arguments
    ---------
    file_path : PathLike
        The path to the program excel file.
    """

    def __init__(self, file_path: PathLike) -> None:
        """Initialize the program from an excel configuration file.
        """
        file_path = sanitize_file_path(file_path, suffix='.xlsx', check_exists=True)
        self.root_dir = file_path.parent
        logger.info(f"Loading program data from {file_path}...")
        # Read the first worksheet, with the conference metadata.
        schema_ = schema.conference_schema()
        df = self._read_sheet(file_path, schema_)
        key_col, value_col = schema_.col_headers()
        metadata = df.dropna(subset=[key_col]).set_index(key_col)[value_col].to_dict()
        self.conference_name = metadata['conference_name']
        self.location = metadata['location']
        self.start_date = self.parse_date(metadata['start_date'])
        self.end_date = self.parse_date(metadata['end_date'])
        # Read the program worksheet, with the list of sessions.
        self.session_dict = {}
        for _, row in self._read_sheet(file_path, schema.program_schema()).iterrows():
            session = Session.from_dataframe_row(row)
            self.session_dict[session.id] = session
        # Read the mapping between host ids and screen ids.
        self.screen_dict = {}
        for _, row in self._read_sheet(file_path, schema.hosts_schema()).iterrows():
            host_id, screen_id = row
            self.screen_dict[host_id] = screen_id
        # Read all the session sheets.
        for session_id, session in self.session_dict.items():
            for _, row in self._read_sheet(file_path, schema.session_schema(session_id)).iterrows():
                poster = Poster.from_dataframe_row(row)
                session.add(poster)

    @staticmethod
    def _read_sheet(file_path: PathLike, schema_: schema.SheetSchema) -> pd.DataFrame:
        """Read a worksheet from the program excel file and return it as a dataframe.

        Arguments
        ---------
        file_path : PathLike
             The path to the program excel file.

        schema_ : SheetSchema instance
             The schema of the worksheet to read.

        Returns
        -------
        df : pandas.DataFrame
             The worksheet content as a dataframe.
        """
        logger.debug(f"Reading worksheet {schema_.name}...")
        df = pd.read_excel(file_path, sheet_name=schema_.name, header=0)
        if tuple(df.columns) != schema_.col_headers():
            raise ValueError(
                f"Invalid columns in '{schema_.name}'. "
                f"Expected {schema_.col_headers()}, got {tuple(df.columns)}"
            )
        logger.debug(f"Done, {len(df)} row(s) read out.")
        return df

    @staticmethod
    def parse_datetime(datetime_str: str) -> date:
        """Parse a datetime string in the proper schema format and return a datetime object.

        Arguments
        ---------
        datetime_str : str
            The datetime string to parse.

        Returns
        -------
        datetime : datetime.datetime
            The parsed datetime object.
        """
        return datetime.strptime(datetime_str, schema.DATETIME_FORMAT)

    @staticmethod
    def parse_date(date_str: str) -> date:
        """Parse a date string in the proper schema format and return a date object.

        Arguments
        ---------
        date_str : str
            The date string to parse.

        Returns
        -------
        date : datetime.date
            The parsed date object.
        """
        return datetime.strptime(date_str, schema.DATE_FORMAT).date()

    def random_poster(self) -> Poster:
        """Return a random poster from the program.
        """
        session = random.choice(list(self.session_dict.values()))
        return random.choice(session.posters)
