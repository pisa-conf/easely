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

import datetime
import pathlib
import random
import socket
from dataclasses import dataclass, field

import pandas as pd

from . import schema
from .logging_ import logger
from .paths import WorkspaceLayout, contribution_file_name, sanitize_file_path
from .__qt__ import QtGui
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

    def _load_pixmap(self, root_dir: pathlib.Path, workspace_dir: pathlib.Path,
        width: int = None, suffix: str = ".png") -> QtGui.QPixmap:
        """Load a pixmap pertaining to the poster from the file system.

        Note that, unlike the original version of the program, we are always loading
        image files on the fly and never caching them in the Poster object, even for
        the slideshow display. This comes at a (small) cost in computational time,
        but it simplifies the implementation.

        Arguments
        ---------
        root_dir : pathlib.Path
            The path to the root directory for the conference, containing all the files.

        workspace_dir : pathlib.Path
            The path to the workspace directory containing the files of the given type
            (e.g., qrcodes, presenters, etc.).

        suffix : str
            The file suffix for the target file, including the dot, e.g., ".png".

        Returns
        -------
        pixmap : QtGui.QPixmap
            The loaded pixmap, scaled to the given width if specified.
        """
        file_name = contribution_file_name(self.friendly_id, suffix)
        file_path = root_dir / workspace_dir / file_name
        pixmap = QtGui.QPixmap(str(file_path))
        if width is not None:
            pixmap = pixmap.scaledToWidth(width, QtCore.Qt.SmoothTransformation)
        return pixmap

    def qrcode_pixmap(self, root_dir: pathlib.Path, width: int = None) -> QtGui.QPixmap:
        """Load the QPixmap object with the QR code.
        """
        return self._load_pixmap(root_dir, WorkspaceLayout.QRCODES, width)

    def headshot_pixmap(self, root_dir: pathlib.Path, width: int = None) -> QtGui.QPixmap:
        """Load the QPixmap object with the presenter headshot.
        """
        return self._load_pixmap(root_dir, WorkspaceLayout.CROPPED_HEADSHOTS, width)

    def poster_pixmap(self, root_dir: pathlib.Path, width: int = None) -> QtGui.QPixmap:
        """Load the QPixmap object with the actual poster.
        """
        return self._load_pixmap(root_dir, WorkspaceLayout.RASTERED_POSTERS, width)


@dataclass
class Session:

    """Session descriptor.
    """

    id: int
    title: str
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
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

    def ongoing(self, current_datetime: datetime.datetime = None) -> bool:
        """Return True if the session is ongoing.

        Arguments
        ---------
        current_datetime : datetime.datetime, optional
            The datetime to check against. If None, the current datetime is used.

        Returns
        -------
        ongoing : bool
            True if the session is ongoing, False otherwise.
        """
        if current_datetime is None:
            current_datetime = datetime.datetime.now()
        # Note we want one <= and one <!
        return self.start_datetime <= current_datetime < self.end_datetime


class PosterRoster(list):

    """Poster roster descriptor.

    This is a small convenience class to keep track of the posters assigned to
    a given screen.

    .. warning::

       This class is currently inheriting from list, mainly for backward
       compatibility, but we should think hard about whether this is a good
       idea. We should look into which kind of interfaces we really need and
       implement just those.

    Arguments
    ---------
    session : Session instance
        The session the roster is associated with.
    """

    def __init__(self, session: Session, root_dir: pathlib.Path) -> None:
        """Constructor.
        """
        super().__init__()
        self.session = session
        self.root_dir = root_dir


class Program:

    """Conference program descriptor.

    Arguments
    ---------
    file_path : PathLike
        The path to the program excel file.

    host_name : str, optional
        The name of the host computer. If None, the current hostname is used.
        This is handy for testing and debugging, to simulate the display on
        different hosts.

    display_datetime : datetime.datetime, optional
        The datetime to use for the display. If None, the current datetime is used.
        This is handy for testing and debugging, to simulate the display at
        different times during (or before/after) the conference.
    """

    def __init__(self, file_path: PathLike, screen_id: int = None,
                 display_datetime: datetime.datetime = None) -> None:
        """Initialize the program from an excel configuration file.
        """
        file_path = sanitize_file_path(file_path, suffix='.xlsx', check_exists=True)
        self.root_dir = file_path.parent
        self.display_datetime = display_datetime
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
        self.screen_dict = {screen: host for _, (host, screen) in
            self._read_sheet(file_path, schema.hosts_schema()).iterrows()}
        # And, since we are at it, cache the screen id for the current host.
        self.host_name = socket.gethostname()
        self.screen_id = screen_id or self.screen_dict.get(self.host_name)
        logger.debug(f"Host {self.host_name} mapped to screen id {self.screen_id}.")
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
    def parse_datetime(datetime_str: str) -> datetime.datetime:
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
        return datetime.datetime.strptime(datetime_str, schema.DATETIME_FORMAT)

    @staticmethod
    def parse_date(date_str: str) -> datetime.date:
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
        return datetime.datetime.strptime(date_str, schema.DATE_FORMAT).date()

    def ongoing_sessions(self) -> list[Session]:
        """Return the list of ongoing sessions.

        Arguments
        ---------
        current_datetime : datetime.datetime, optional
            The datetime to check against. If None, the current datetime is used.

        Returns
        -------
        ongoing_sessions : list[Session]
            The list of ongoing sessions.
        """
        return [session for session in self.session_dict.values() if session.ongoing(self.display_datetime)]

    def poster_roster(self) -> PosterRoster:
        """Return the list of posters assigned to the current screen at the
        given display time.

        .. warning::

           At this moment we are not making any effort to prevent the user from
           mixing sessions in the roster, but we probably should.

        Returns
        -------
        roster : list[Poster]
            The list of posters assigned to the current screen.
        """
        if self.screen_id is None:
            raise ValueError(f"Host {self.host_name} not mapped to any screen.")
        roster = None
        for session in self.ongoing_sessions():
            logger.debug(f"Session '{session.title}' ongoing with {len(session)} poster(s).")
            for poster in session.posters:
                if poster.screen_id == self.screen_id:
                    if roster is None:
                        roster = PosterRoster(session, self.root_dir)
                    roster.append(poster)
        logger.debug(f"Roster for screen {self.screen_id} includes {len(roster)} poster(s).")
        return roster

    def random_poster(self) -> Poster:
        """Return a random poster from the program.
        """
        session = random.choice(list(self.session_dict.values()))
        return random.choice(session.posters)
