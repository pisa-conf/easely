# Copyright (C) 2022, luca.baldini@pi.infn.it
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

from collections import Counter
import datetime
import os
import random

import pandas as pd
#pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from pisameet import logger, MISSING_PICTURE_PATH, MISSING_POSTER_PATH, MISSING_QRCODE_PATH



DATE_FORMAT =  '%d/%m/%Y'
DATE_PRETTY_FORMAT = '%A, %B %d, %Y'
DATETIME_FORMAT =  f'{DATE_FORMAT} %H:%M'


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

    def __init__(self, first_name: str, last_name: str, affiliation: str) -> None:
        """Constructor
        """
        self.first_name = first_name
        self.last_name = last_name
        self.affiliation = affiliation

    def full_name(self) -> str:
        """Return the presenter full name.
        """
        return f'{self.first_name} {self.last_name}'

    def __str__(self) -> str:
        """String formatting.
        """
        return f'{self.full_name()} ({self.affiliation})'



class Poster:

    """Poster descriptor.

    Arguments
    ---------
    friedly_id : int
        The human-readable identifier assigned to the poster by indico.

    db_id : int
        The unique identifier assigned by indico (this can be used to retrieve the
        material online).

    screen_id :  int
        The identifier of the screen the poster needs to be projected on.

    title : str
        The poster title.

    presenter : Presenter instance
        The poster presenter.
    """

    #pylint: disable=too-many-instance-attributes, too-many-arguments

    def __init__(self, friendly_id: int, db_id: int, screen_id: int,
        title: str, presenter) -> None:
        """Constructor.
        """
        self.friendly_id = int(friendly_id)
        self.db_id = int(db_id)
        self.screen_id = int(screen_id)
        self.title = title
        self.presenter = presenter
        self.poster_pixmap = None
        self.presenter_pixmap = None
        self.qrcode_pixmap = None
        self.session = None
        self.session_index = None
        self.program_index = None

    @classmethod
    def from_df_row(cls, row):
        """Create a PosterSession object from a dataframe row.
        """
        args = [row[col_name] for col_name in PosterRoster.SESSION_COL_NAMES]
        if not pd.isna(args[2]):
            args[2] = int(args[2])
        return cls(*args[:-3], Presenter(*args[-3:]))

    def short_title(self, max_chars=40):
        """Return a shortened version of the title, trimmed to a fixed maximum
        number of characters if too long.
        """
        if len(self.title) <= max_chars:
            return self.title.ljust(max_chars)
        return f'{self.title[:max_chars - 3]}...'

    @staticmethod
    def _load_pixmap_w(file_path: str, width: int):
        """Load the underlying pixmap with a fixed width.
        """
        logger.debug('Loading image data from %s...', file_path)
        return QPixmap(file_path).scaledToWidth(width, Qt.SmoothTransformation)

    @staticmethod
    def _load_pixmap_h(file_path: str, height: int):
        """Load the underlying pixmap with a fixed height.
        """
        logger.debug('Loading image data from %s...', file_path)
        return QPixmap(file_path).scaledToHeight(height, Qt.SmoothTransformation)

    @staticmethod
    def load_default_pixmaps(poster_width: int, portrait_height: int):
        """
        """
        return Poster._load_pixmap_w(MISSING_POSTER_PATH, poster_width),\
            Poster._load_pixmap_h(MISSING_QRCODE_PATH, portrait_height)

    def load_pixmaps(self, poster_file_path, presenter_file_path, qrcode_file_path,
        poster_width, portrait_height):
        """Load all the necessary poster data.
        """
        #pylint: disable=too-many-arguments
        logger.info('Loading data for poster %s...', self)
        self.poster_pixmap = self._load_pixmap_w(poster_file_path, poster_width)
        self.presenter_pixmap = self._load_pixmap_h(presenter_file_path, portrait_height)
        self.qrcode_pixmap = self._load_pixmap_h(qrcode_file_path, portrait_height)

    def unload_pixmaps(self):
        """Delete the references to the pixaps, so that the Python garbage collector
        can free the memory at the next round.

        This can be used, e.g., in the poster browser so that we do not put
        too many pixmaps in memory as we browse the program.
        """
        self.poster_pixmap = None
        self.presenter_pixmap = None
        self.qrcode_pixmap = None

    def pretty_print(self, max_chars=40):
        """Poster pretty print.
        """
        title = self.short_title(max_chars)
        return f'[{self.friendly_id:03}] {title} ({self.presenter.full_name()})'

    def __str__(self):
        """String formatting.
        """
        return self.pretty_print()



class PosterSession:

    """Poster session descriptor.
    """

    def __init__(self, id_: int, title: str, start: str , end: str):
        """Constructor
        """
        self.id_ = int(id_)
        self.title = title
        self.start = self.parse_datetime(start)
        self.end = self.parse_datetime(end)

    def parse_datetime(self, text: str):
        """Parse a datetime string in the proper format.
        """
        # pylint: disable=broad-except
        try:
            return datetime.datetime.strptime(text, DATETIME_FORMAT)
        except Exception as exception:
            logger.warning('Invalid date and/or time for session %s (%s).', self.id_, exception)
            return None

    @classmethod
    def from_df_row(cls, row):
        """Create a PosterSession object from a dataframe row.
        """
        return cls(*[row[col_name] for col_name in PosterRoster.PROGRAM_COL_NAMES])

    def ongoing(self, current_datetime=None) -> bool:
        """Return True if the session is ongoing.
        """
        if current_datetime is None:
            current_datetime = datetime.datetime.now()
        # Note we want one <= and one <!
        return self.start is not None and self.end is not None and \
            self.start <= current_datetime < self.end

    def __str__(self):
        """String formatting.
        """
        return f'Session {self.id_} ({self.title})'



class PosterCollectionBase:

    """Base class for a poster collection.

    This base class has all the pointers to the relevant directory structure, as
    well as a reference to the underlying pandas data frame containing the
    program (and read from the first sheet of the excel configuration file).
    Note that parsing the session sheets of the excel file is delegated to the
    sub-classes.

    See the PosterRoster and PosterProgram for concrete examples of sub-classes.

    Arguments
    ---------
    config_file_path : str
        The path to the excel config file with the poster program.

    root_folder_path : str
        The path to the root folder containing the session material---if None
        defaults to the directory in which the configuration file is placed.
    """

    PROGRAM_SHEET_NAME = 'Program'
    PROGRAM_COL_NAMES = (
        'Session ID', 'Session Name', 'Start Date', 'End Date'
        )
    PROGRAM_COL_DTYPES = {'Session ID': int, 'Start Date': str, 'End Date': str}
    SESSION_COL_NAMES = (
        'Friendly ID', 'DB ID', 'Screen ID', 'Title', 'First Name', 'Last Name', 'Affiliation'
        )
    SESSION_COL_DTYPES = {'Friendly ID': int, 'DB ID': int, 'Screen ID': int}
    POSTER_FOLDER_NAME = 'posters_raster'
    PRESENTER_FOLDER_NAME = 'presenters_crop'
    QRCODE_FOLDER_NAME = 'qrcodes'

    def __init__(self, config_file_path: str, root_folder_path: str = None) -> None:
        """Constructor.
        """
        self.config_file_path = config_file_path
        if root_folder_path is None:
            root_folder_path = os.path.dirname(config_file_path)
        self.root_folder_path = os.path.abspath(root_folder_path)
        self.poster_folder_path = os.path.join(self.root_folder_path, self.POSTER_FOLDER_NAME)
        self.presenter_folder_path = os.path.join(self.root_folder_path, self.PRESENTER_FOLDER_NAME)
        self.qrcode_folder_path = os.path.join(self.root_folder_path, self.QRCODE_FOLDER_NAME)
        logger.debug('Reading %s sheet from %s...', self.PROGRAM_SHEET_NAME, config_file_path)
        self._program_df = pd.read_excel(config_file_path, self.PROGRAM_SHEET_NAME,
            dtype=self.PROGRAM_COL_DTYPES)
        logger.debug('Done, %d row(s) found.', len(self._program_df))

    def session_list(self):
        """Return a list with all the PosterSession objects.

        Note we are filtering the sessions to avoid having multiple copies of the
        same entry in the menu. This is horrible and should be streamlined.
        """
        sessions = []
        visited = []
        for _, row in self._program_df.iterrows():
            session = PosterSession.from_df_row(row)
            if session.title not in visited:
                visited.append(session.title)
                sessions.append(session)
        return sessions
        #return [PosterSession.from_df_row(row) for _, row in self._program_df.iterrows()]

    def session_data_frame(self, session_id):
        """Return a pandas data frame with all the data for a given session.
        """
        # pylint: disable=broad-except
        logger.info('Reading data for session %d...', session_id)
        try:
            return pd.read_excel(self.config_file_path, str(session_id), dtype=self.SESSION_COL_DTYPES)
        except Exception as exception:
            logger.warning('Data not available for session %s: %s', session_id, exception)
            return None

    def session_poster_list(self, session_id, sort=True):
        """Return a list of Poster objects for a given session data frame.
        """
        data_frame = self.session_data_frame(session_id)
        if data_frame is None:
            return []
        poster_list = [Poster.from_df_row(row) for _, row in data_frame.iterrows()]
        if sort:
            poster_list.sort(key=lambda item: item.friendly_id)
        return poster_list

    def poster_dict(self):
        """Return a dictionary of lists of Poster objects, indexed by session.
        """
        return {session: self.session_poster_list(session.id_) for session in self.session_list()}

    @staticmethod
    def _image_file_name(poster_id: int):
        """Return the file name for any of the pixmaps for a given poster.

        The rule, here, is that all the pixmpas share the same file name
        (e.g., 003.png) and live in different folders.
        """
        return f'{poster_id:03d}.png'

    def _image_path_base(self, poster_id: int, folder_name: str, default: str):
        """Generic function to build the path to the actual pixmap file for a given poster.

        Arguments
        ---------
        poster_id : int
            The poster friendly ID.

        folder_name : str
            The name of the folder containing the pixmaps, relative to the root folder.

        default : str
            The path to the default pixmap, in case the proper one does not exist.
        """
        file_name = self._image_file_name(poster_id)
        file_path = os.path.join(self.root_folder_path, folder_name, file_name)
        if not os.path.exists(file_path):
            logger.warning('Could not find %s...', file_path)
            return default
        return file_path

    def poster_image_path(self, poster_id):
        """Return the path to the poster image.
        """
        return self._image_path_base(poster_id, self.POSTER_FOLDER_NAME, MISSING_POSTER_PATH)

    def missing_poster_image(self, poster_id):
        """
        """
        return self.poster_image_path(poster_id) == MISSING_POSTER_PATH

    def presenter_image_path(self, poster_id):
        """Return the path to the presenter image.
        """
        return self._image_path_base(poster_id, self.PRESENTER_FOLDER_NAME, MISSING_PICTURE_PATH)

    def missing_presenter_image(self, poster_id):
        """
        """
        return self.presenter_image_path(poster_id) == MISSING_PICTURE_PATH

    def qrcode_image_path(self, poster_id):
        """Return the path to the qrcode image.
        """
        return self._image_path_base(poster_id, self.QRCODE_FOLDER_NAME, MISSING_QRCODE_PATH)

    def missing_qrcode_image(self, poster_id):
        """
        """
        return self.qrcode_image_path(poster_id) == MISSING_QRCODE_PATH

    def load_poster_pixmaps(self, poster, poster_width, portrait_height):
        """Load all the necessary pixmaps for a given poster.
        """
        poster_id = poster.friendly_id
        poster_file_path = self.poster_image_path(poster_id)
        presenter_file_path = self.presenter_image_path(poster_id)
        qrcode_file_path = self.qrcode_image_path(poster_id)
        poster.load_pixmaps(poster_file_path, presenter_file_path, qrcode_file_path,
            poster_width, portrait_height)



class PosterRoster(PosterCollectionBase, list):

    """Poster roster description.

    Arguments
    ---------
    config_file_path : str
        The path to the excel config file with the poster program.

    root_folder_path : str
        The path to the root folder containing the session material.

    screen_id : int
        The screen identifier for the poster roster.
    """

    def __init__(self, config_file_path: str, root_folder_path: str, screen_id: int,
        display_date: str = None) -> None:
        """Constructor.

        Note there are two subtle tweaks that we did in 2024, to adapt to the new
        poster session scheme, where multiple sessions are displayed in parallel:
        we removede the break within the main for loop, so that the code will look
        into *all* the sessions happening at a given time, and we assign the session
        name deep inside the loop, so that, for any given scree ID we pick the proper
        session. Note this mechanism is fragile and relies on the fact that we
        do not mix sessions within each screen.
        """
        PosterCollectionBase.__init__(self, config_file_path, root_folder_path)
        list.__init__(self)
        self.screen_id = screen_id
        self.session = None
        logger.info('Populating session list...')
        for _, program_row in self._program_df.iterrows():
            session = PosterSession.from_df_row(program_row)
            if not session.ongoing(display_date):
                continue
            logger.info('Parsing ongoing %s...', session)
            try:
                session_df = pd.read_excel(config_file_path, f'{session.id_}')
                for _, session_row in session_df.iterrows():
                    poster = Poster.from_df_row(session_row)
                    if poster.screen_id == self.screen_id:
                        self.append(poster)
                        self.session = session
            except ValueError as exception:
                logger.warning('Data not available for session %s: %s', session.id_, exception)
            # The following two lines have been modified to support multiple
            # poster sessions in parallel---the break is removed and the session
            # assigned is moved within the for loop.
            #self.session = session
            #break
        if len(self) == 0:
            logger.warning('Empty poster roster for screen %d', self.screen_id)

    def load_pixmaps(self, poster_width: int, portrait_height: int):
        """Load all the poster pixmaps with the proper dimensions.
        """
        for poster in self:
            self.load_poster_pixmaps(poster, poster_width, portrait_height)

    def __str__(self):
        """String formatting.
        """
        return f'Roster for screen {self.screen_id}\n' + '\n'.join([str(poster) for poster in self])



class PosterProgram(PosterCollectionBase, dict):

    """Full description of a poster program.

    The program is organized as dictionary indexed by PosterSession and whose
    values are Poster objects.
    """

    def __init__(self, config_file_path: str, root_folder_path: str = None) -> None:
        """Constructor
        """
        PosterCollectionBase.__init__(self, config_file_path, root_folder_path)
        dict.__init__(self, self.poster_dict())
        self.__flattened_list = []
        program_index = 0
        for session, posters in self.items():
            for i, poster in enumerate(posters):
                poster.session = session
                poster.program_index = program_index
                poster.session_index = i
                program_index += 1
                self.__flattened_list.append(poster)

    def select_by_program_index(self, index):
        """Select a poster by program index.
        """
        return self.__flattened_list[index % len(self.__flattened_list)]

    def select_by_session_index(self, session, index):
        """Select a poster by session index.
        """
        posters = self[session]
        return posters[index % len(posters)]

    def random_poster(self):
        """Return a random poster object from the program.
        """
        logger.debug('Picking random poster from the program...')
        session = random.choice(list(self))
        logger.debug(session)
        poster = random.choice(self[session])
        logger.debug(poster)
        return poster

    def dump_report(self):
        """Dump a program report for diagnostics purposes.
        """
        basic_stats = {'posters': 0, 'pics': 0, 'qrcodes': 0}
        missing_stats = {'posters': 0, 'pics': 0, 'qrcodes': 0}
        missing_pics = []
        missing_posters = []
        for session, posters in self.items():
            logger.info(session)
            cnt = Counter([poster.screen_id for poster in posters])
            cnt = dict(sorted(cnt.items()))
            num_posters = len(posters)
            mult = cnt.values()
            num_screens = len(mult)
            mean_mult = num_posters / num_screens
            logger.info('%d posters on %d screen(s), multiplicity: %d--%d (average %.2f)',
                num_posters, num_screens, min(mult), max(mult), mean_mult)
            for poster in posters:
                if self.missing_poster_image(poster.friendly_id):
                    missing_stats['posters'] += 1
                    missing_posters.append(poster)
                else:
                    basic_stats['posters'] += 1
                if self.missing_presenter_image(poster.friendly_id):
                    missing_stats['pics'] += 1
                    if not self.missing_poster_image(poster.friendly_id):
                        missing_pics.append(poster)
                else:
                    basic_stats['pics'] += 1
                if self.missing_qrcode_image(poster.friendly_id):
                    missing_stats['qrcodes'] += 1
                else:
                    basic_stats['qrcodes'] += 1
            logger.info('Screen statistics: %s', cnt)
        logger.info(f'Basic statistics: {basic_stats}')
        logger.info(f'Missing elements: {missing_stats}')
        logger.info(f'Oprhan posters with no presenter pic:')
        for poster in missing_pics:
            logger.info(poster)
        logger.info(f'Missing posters:')
        for poster in missing_posters:
            logger.info(poster)
