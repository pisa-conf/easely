# Copyright (C) 2021--2026, the easely team.
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

"""Graphical user interface.
"""

import datetime
import pathlib
import time
from enum import Enum, IntEnum, auto

import pandas as pd

from .__qt__ import QtCore, QtGui, QtWidgets
from .logging_ import logger
from .magic import read_magic_file
from .profile import psstatus
from .program import Poster, PosterRoster, Program


class FadingEffect(QtWidgets.QGraphicsOpacityEffect):

    """Graphic effect for picture fade-in/out.

    This is simple graphic effect allowing a fade-in/out effect to a gradual change in the
    opacity. Internally, the transitions are controlled via a QTimer() object increasing
    or decreasing the opacity by a fixed amount (the _step class member) at each timeout.

    Arguments
    ---------
    step : float
        The basic opacity step used when increasing/decreasing the opacity.

    interval : int
        The basic time interval (in ms) during the transitions.
    """

    def __init__(self, step: float = 0.025, interval: int = 5):
        """Constructor.
        """
        super().__init__()
        self.setOpacity(1.)
        self._step = step
        self._interval = interval
        self._timer = QtCore.QTimer()
        self._timer.start(self._interval)
        logger.debug(f"Opacity fade time set to {self.fade_time():.3f} s")

    def fade_time(self):
        """Return the total fade-in/out time in seconds, i.e., the time that it
        takes for the opacity to change all the way from 0 to 1 or vice-versa.
        """
        return 1.e-3 * self._interval / self._step

    def _decrease_opacity(self):
        """Decrease the opacity by one step.

        Since this is typically controlled by the underlying QTimer object, when
        the opacity reaches (or crosses) zero the timer is disconnected from all
        the slots, and the opacity is set to 0 (fully opaque).
        """
        opacity = self.opacity() - self._step
        if opacity <= 0.:
            self._timer.timeout.disconnect()
            self.setOpacity(0.)
        self.setOpacity(opacity)

    def _increase_opacity(self):
        """Increase the opacity by one step.

        Since this is typically controlled by the underlying QTimer object, when
        the opacity reaches (or crosses) one the timer is disconnected from all
        the slots, and the opacity is set to 1 (fully transparent).
        """
        opacity = self.opacity() + self._step
        if opacity >= 1.:
            self._timer.timeout.disconnect()
            self.setOpacity(1.)
        self.setOpacity(opacity)

    def fade_in(self, start_from_zero=True):
        """Fade in effect, i.e., gradually change opacity to 1.
        """
        if start_from_zero:
            self.setOpacity(0.)
        self._timer.timeout.connect(self._increase_opacity)

    def fade_out(self, start_from_one=True):
        """Fade in effect, i.e., gradually change opacity to 0.
        """
        if start_from_one:
            self.setOpacity(1.)
        self._timer.timeout.connect(self._decrease_opacity)


class WidgetName(str, Enum):

    """Enum for the names of the widgets in the GUI.

    This is used to set the object name of the widgets, which is then used in
    the qss stylesheet to set their style.
    """

    TITLE = "title"
    SUBTITLE = "subtitle"
    STATUS_MESSAGE = "status_message"
    HEADSHOT = "headshot"
    QR_CODE = "qr_code"
    PRESENTER_NAME = "presenter_name"
    PRESENTER_AFFILIATION = "presenter_affiliation"
    ROSTER_TABLE = "roster_table"


class RosterTable(QtWidgets.QTableWidget):

    """Custom QTableWidget to display a poster roster.

    In addition to the basic functionality of the base class, this is designed to
    highlight one row at a time (e.g., by setting a different color) in order to visually
    indicate the poster being displayed at any given time.

    Arguments
    ---------
    default_rgb : int
        The default value of the three RGB channels for the default
        (i.e., not highlighted) color.
    """

    def __init__(self, parent: QtWidgets.QWidget, default_rgb: int = 175,
                 col_spans: tuple = (0.075, 0.675, 0.25)) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self._col_spans = col_spans
        self.setColumnCount(3)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.setShowGrid(False)
        self.setEnabled(False)
        self.setObjectName(WidgetName.ROSTER_TABLE)
        self._default_color = QtGui.QColor(default_rgb, default_rgb, default_rgb)
        self._highlight_color = QtGui.QColor(0, 0, 0)
        self._highlighted_row = None

    def resizeEvent(self, event):
        """Overloaded method to control the column widths when the table is resized.
        """
        super().resizeEvent(event)
        width = self.viewport().width()
        for i, span in enumerate(self._col_spans):
            self.setColumnWidth(i, int(span * width))

    def set_text(self, row: int, col: int, text: str) -> None:
        """Set the text for a given cell.

        Note the item is rendered with the default foreground color upon insertion.

        Arguments
        ---------
        row : int
            The row identifier.

        col : int
            The column identifier.

        text : str
            The text to be displayed.
        """
        item = QtWidgets.QTableWidgetItem(text)
        item.setForeground(self._default_color)
        self.setItem(row, col, item)

    def set_poster(self, row: int, poster: Poster, title_length: int = 65) -> None:
        """Populate a given row with the poster information.

        Arguments
        ---------
        row : int
            The row identifier.

        poster : program.Poster object
            The poster to be displayed on a given row.
        """
        self.set_text(row, 0, f'[{poster.friendly_id}]')
        self.set_text(row, 1, f'{poster.short_title(title_length)}'.ljust(title_length))
        self.set_text(row, 2, f'{poster.presenter.full_name()}')

    def set_roster(self, roster: PosterRoster) -> None:
        """Populate the entire table with a poster roster.

        Arguments
        ---------
        roster : PosterRoster
            The poster roster to be displayed in the table.
        """
        self.clear()
        self.setRowCount(len(roster))
        for row, poster in enumerate(roster):
            self.set_poster(row, poster)

    def set_current_row(self, row: int) -> None:
        """Highlight a given row.

        Arguments
        ---------
        row : int
            The row identifier.
        """
        for col in range(self.columnCount()):
            if self._highlighted_row is not None:
                try:
                    self.item(self._highlighted_row, col).setForeground(self._default_color)
                except AttributeError:
                    logger.warning(f'Could not highlight row {self._highlighted_row, col}')
            self.item(row, col).setForeground(self._highlight_color)
        self._highlighted_row = row


class ScreenHeader(QtWidgets.QWidget):

    """Class describing the screen header.
    """

    def __init__(self, parent: QtWidgets.QWidget = None, title: str = None) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self.program = parent.program
        self._roster = None
        self.setLayout(QtWidgets.QGridLayout())
        # Create all the widgets and place them in the grid layout.
        self.title_label = self._add_qlabel(WidgetName.TITLE, 0, 0, 1, 3)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.subtitle_label = self._add_qlabel(WidgetName.SUBTITLE, 1, 0, 1, 3)
        self.subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        self.headshot_label = self._add_qlabel(WidgetName.HEADSHOT, 2, 0)
        self.qrcode_label = self._add_qlabel(WidgetName.QR_CODE, 2, 1)
        self.roster_table = RosterTable(self)
        self.layout().addWidget(self.roster_table, 2, 2)
        self.presenter_name_label = self._add_qlabel(WidgetName.PRESENTER_NAME, 4, 0, 1, 2)
        self.presenter_affiliation_label = self._add_qlabel(WidgetName.PRESENTER_AFFILIATION, 5, 0, 1, 2)
        self.message_label = self._add_qlabel(WidgetName.STATUS_MESSAGE, 4, 2, 2, 1)
        self.message_label.setAlignment(QtCore.Qt.AlignBottom)
        self.set_title(self.program.pretty_title())

    def _add_qlabel(self, object_name: WidgetName, row: int, col: int, row_span: int = 1,
        col_span: int = 1) -> QtWidgets.QLabel:
        """Create a new label with the given object name, and return it.

        This is a small helper function to help setting the object names in a consistent
        fashion, which is instrumental for the qss stylesheet to work properly.

        Arguments
        ---------
        object_name : WidgetName
            The name of the widget to be created.

        text : str, optional
            The text to be displayed on the label.

        align : QtCore.Qt.AlignmentFlag, optional
            The alignment of the text on the label.
        """
        label = QtWidgets.QLabel(self)
        label.setObjectName(object_name)
        self.layout().addWidget(label, row, col, row_span, col_span)
        return label

    def set_title(self, text: str = None) -> None:
        """Set the title.
        """
        self.title_label.setText(text or "")

    def set_subtitle(self, text: str = None) -> None:
        """Set the subtitle.
        """
        self.subtitle_label.setText(text or "")

    def set_status_message(self, text: str = None) -> None:
        """Set the status text label.
        """
        self.message_label.setText(text or "")

    def clear(self):
        """Generic function to clear the relevant QLabel objects in the header.
        """
        self.message_label.setText("")
        self.presenter_name_label.setText("")
        self.presenter_affiliation_label.setText("")
        self.roster_table.clear()
        self.headshot_label.clear()
        self.qrcode_label.clear()

    def set_roster(self, roster: PosterRoster) -> None:
        """Set the poster roster for the table.
        """
        self._roster = roster
        self.set_subtitle(self._roster.session.title)

    def _update_pixmaps(self, poster: Poster) -> None:
        """Update the two pixmaps.
        """
        self.headshot_label.setPixmap(poster.headshot_pixmap(self.program.root_dir))
        self.qrcode_label.setPixmap(poster.qrcode_pixmap(self.program.root_dir))

    def _update_presenter(self, poster: Poster) -> None:
        """Update the presenter name and affiliation.
        """
        presenter = poster.presenter
        self.presenter_name_label.setText(presenter.full_name())
        self.presenter_affiliation_label.setText(presenter.short_affiliation())

    def set_poster(self, poster: Poster) -> None:
        """Set the poster for the header.
        """
        self._update_pixmaps(poster)
        self._update_presenter(poster)
        self.roster_table.clear()
        self.roster_table.setRowCount(1)
        self.roster_table.set_poster(0, poster)
        self.roster_table.set_current_row(0)

    def update(self, current_poster_id: int) -> None:
        """Update the header based on the roster information and the current poster.
        """
        poster = self._roster[current_poster_id]
        self._update_pixmaps(poster)
        self._update_presenter(poster)
        self.roster_table.set_current_row(current_poster_id)


class DisplayWindowBase(QtWidgets.QWidget):

    """Base class for display windows.
    """

    DISPLAY_TYPE = None

    def __init__(self, **kwargs):
        """Constructor.
        """
        super().__init__()
        # Parse the command-line arguments.
        self.display_mode = kwargs['mode']
        self.poster_width = kwargs['poster_width']
        self.portrait_height = kwargs['portrait_height']
        # Load the program.
        args = kwargs['cfgfile'], kwargs.get('screen_id'), kwargs.get('display_datetime')
        self.program = Program(*args)
        # Setup the widget.
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setColumnMinimumWidth(0, self.poster_width)
        self.header = ScreenHeader(self)
        self.poster_label = QtWidgets.QLabel()
        self.poster_label.setAlignment(QtCore.Qt.AlignHCenter or QtCore.Qt.AlignTop)
        self.debug_label = QtWidgets.QLabel()
        self.layout().addWidget(self.header, 0, 0, 1, 3)
        self.layout().addWidget(self.poster_label, 1, 0, 1, 3)
        # Increase the stretch value for the poster label so that it takes
        # all the available space.
        self.layout().setRowStretch(1, 1)
        self.layout().addWidget(self.debug_label, 2, 0, 1, 3)
        # Setup the fading effect.
        self.fading_effect = FadingEffect()
        if kwargs.get('fading', False):
            self.poster_label.setGraphicsEffect(self.fading_effect)
        # Setup the timer for updating the header.
        self.header_timer = QtCore.QTimer()
        self.header_timer.setInterval(100)
        self.header_timer.timeout.connect(self.update_header_status)
        self.__start_time = time.time()

    def _show(self):
        """Small convenience hook to display the GUI in the proper visualization
        mode, given the command-line options.
        """
        if self.display_mode == 'maximize':
            self.showMaximized()
        elif self.display_mode == 'fullscreen':
            self.showFullScreen()
        else:
            self.show()

    def set_debug_message(self, text):
        """Set the status text label.
        """
        text = f'<font color="gray" size="2">{text}</font><br/>'
        self.debug_label.setText(text)

    def update_debug_label(self):
        """
        """
        uptime = time.time() - self.__start_time
        msg = f'Powered by https://github.com/lucabaldini/easely, {uptime:.1f} s uptime, {psstatus()}'
        self.set_debug_message(msg)

    @staticmethod
    def remaining_time(timer):
        """Return a proxy for the (integer) number of seconds remaining to the
        next trigger of a given counter.

        There is some heuristic involved, here, as we typically want this to
        look good in a GUI field that is not refreshed too often---which is
        why we convert ms to s and add a 0.9 s offset
        """
        return int(0.001 * timer.remainingTime() + 0.75)

    @staticmethod
    def sec_to_msec(sec: float) -> int:
        """Convert a time from seconds to ms.

        Arguments
        ---------
        sec : float
            The time interval in s.

        Return
        ------
            The time interval in ms, rounded to the nearest integer.
        """
        return int(round(1.e3 * sec))

    def update_header_status(self):
        """Update the header information.
        """
        self.header.set_status_message(self.status_message())

    def status_message(self):
        """Do nothing hook to be reimplemented by derived classes.
        """
        raise NotImplementedError



class SlideShowKeyMap(IntEnum):

    """Basic mapping of the four-key keyboard.
    """

    ADVANCE = 1
    PAUSE = 2
    BACKUP = 3
    RELOAD = 5



class SlideShowStatus(Enum):

    """Status of the slideshow finite-state machine.
    """

    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()



class SlideShow(DisplayWindowBase):

    """Basic slideshow class.
    """

    DISPLAY_TYPE = 'Slideshow'
    VALID_KEYS = [str(key.value) for key in SlideShowKeyMap]
    TIP = 'use the arrows to navigate the posters or the mid button to pause'
    RUNNING_MSG = f'SlideShow running, %d s to the next poster ({TIP})'
    PAUSED_MSG = f'SlideShow paused, %d s to restart ({TIP})'

    def __init__(self, **kwargs):
        """Constructor.
        """
        super().__init__(**kwargs)
        self.advance_interval = self.sec_to_msec(kwargs['advance_interval'])
        self.pause_interval = self.sec_to_msec(kwargs['pause_interval'])
        self.__status = SlideShowStatus.STOPPED
        self.__current_index = 0
        # Setup the timers.
        self.advance_timer = QtCore.QTimer()
        self.advance_timer.setInterval(self.advance_interval)
        self.advance_timer.timeout.connect(self.advance)
        self.resume_timer = QtCore.QTimer()
        self.resume_timer.setInterval(self.pause_interval)
        self.resume_timer.setSingleShot(True)
        self.resume_timer.timeout.connect(self.resume)
        self.reload_timer = QtCore.QTimer()
        self.reload_timer.setInterval(10000)
        self.reload_timer.timeout.connect(self._check_reload)
        # We're good to go!
        self._load_roster()
        self.header_timer.start()
        self.reload_timer.start()

    def _check_reload(self):
        """
        """
        if read_magic_file():
            self._load_roster()
            return
        # Deal with the case where the session is empty.
        if self.poster_roster.session is None:
            return
        if not self.poster_roster.session.ongoing(self.program.display_datetime):
            logger.info(f'Session {self.poster_roster.session} is over, reloading the program...')
            self._load_roster()

    def _load_roster(self):
        """Load a given session from the underlying configuration file.
        """
        logger.info('Loading poster roster...')
        self.stop()
        self.hide()
        self.poster_roster = self.program.poster_roster()
        if len(self.poster_roster) == 0:
            logger.info('Displaying default poster...')
            self._show()
            pix1, pix2 = Poster.load_default_pixmaps(self.poster_width, self.portrait_height)
            self.poster_label.setPixmap(pix1)
            self.header.clear()
            self.header.set_subtitle('')
            self.header.qrcode_label.setPixmap(pix2)
            return
        self.header.set_roster(self.poster_roster)
        subtitle = f'{self.poster_roster.session.title} (screen #{self.program.screen_id})'
        self.header.set_subtitle(subtitle)
        self.header.roster_table.set_roster(self.poster_roster)
        self._show()
        self.display_poster()
        if len(self.poster_roster) > 1:
            self.__current_index = 0
            self.start()

    def running(self):
        """Return True if the Slideshow is running.
        """
        return self.__status == SlideShowStatus.RUNNING

    def start(self):
        """Start the slideshow.
        """
        self.__status = SlideShowStatus.RUNNING
        self.advance_timer.start()

    def stop(self):
        """Stop the slideshow.
        """
        self.__status = SlideShowStatus.STOPPED
        self.advance_timer.stop()

    def pause(self):
        """Pause the slideShow.
        """
        self.__status = SlideShowStatus.PAUSED
        if self.advance_timer.isActive():
            self.advance_timer.stop()
        self.resume_timer.start()

    def resume(self):
        """Resume the slideShow.
        """
        if self.running():
            return
        self.start()
        self.advance()

    def status_message(self):
        """Return the message about the slideshow status to be displayed in the GUI header.
        """
        # pylint: disable=invalid-name
        if self.__status == SlideShowStatus.RUNNING:
            return self.RUNNING_MSG % self.remaining_time(self.advance_timer)
        if self.__status == SlideShowStatus.PAUSED:
            return self.PAUSED_MSG % self.remaining_time(self.resume_timer)
        return ''

    def display_poster(self, index: int = 0) -> None:
        """Display a given poster.
        """
        try:
            self.__current_index = index % len(self.poster_roster)
        except ZeroDivisionError:
            self.__current_index = 0
        self.header.update(self.__current_index)
        poster = self.poster_roster[self.__current_index]
        self.poster_label.setPixmap(poster.poster_pixmap(self.poster_roster.root_dir))
        self.fading_effect.fade_in()

    def advance(self) -> None:
        """Advance to the next image.
        """
        self.display_poster(self.__current_index + 1)

    def backup(self) -> None:
        """Advance to the next image.
        """
        self.display_poster(self.__current_index - 1)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Overloaded method to handle key events.
        """
        # Disengage the keyboard if there is less than two posters.
        if len(self.poster_roster) <= 1:
            return
        # pylint: disable=invalid-name
        key = event.text()
        if not key in self.VALID_KEYS:
            logger.warning(f'Invalid key pressed ({key}).')
            return
        key = int(key)
        if key == SlideShowKeyMap.ADVANCE:
            self.start()
            self.advance()
        elif key == SlideShowKeyMap.BACKUP:
            self.start()
            self.backup()
        elif key == SlideShowKeyMap.PAUSE:
            self.pause()
        elif key == SlideShowKeyMap.RELOAD:
            self._load_roster()



class BrowserKeyMap(IntEnum):

    """Basic mapping of the five-key keyboard for the poster browser.
    """

    EXPAND = QtCore.Qt.Key_Right
    COLLAPSE = QtCore.Qt.Key_Left
    ADVANCE = QtCore.Qt.Key_Down
    BACKUP = QtCore.Qt.Key_Up
    PAUSE = QtCore.Qt.Key_Return



class ProgramTreeWidget(QtWidgets.QTreeWidget):

    """Light wrapper over the QTreeWidget class.
    """

    # Signal emitted when any active key has been pressed.
    key_pressed = QtCore.Signal()

    # Signal emitted when the display of the current poster is requested.
    poster_selected = QtCore.Signal()

    # Signal emitted when the tree view uis requested.
    treeview_selected = QtCore.Signal()

    def __init__(self, width: int, screen_id: bool = False):
        """Constructor.
        """
        super().__init__()
        self.__screen_id = screen_id
        if self.__screen_id:
            self.setColumnCount(3)
            self.setHeaderLabels(['Session/Poster', 'Presenter', 'Screen'])
            self.setColumnWidth(0, int(0.75 * width))
            self.setColumnWidth(1, int(0.20 * width))
            self.header().setStretchLastSection(True)
        else:
            self.setColumnCount(2)
            self.setHeaderLabels(['Session/Poster', 'Presenter'])
            self.setColumnWidth(0, int(0.75 * width))
            self.setColumnWidth(1, int(0.25 * width))
        self.__key_press_events_enabled = True

    def enable_key_press_events(self):
        """Enable key-press events.
        """
        self.__key_press_events_enabled = True

    def disable_key_press_events(self):
        """Disable key-press events.
        """
        self.__key_press_events_enabled = False

    def collapse_unused(self, current_item):
        """Small hook to collapse all the expanded items that are different from
        the current item.

        This effectively prevents the user from being able to expand more than
        one top-level item at a time.
        """
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            if item != current_item and item.isExpanded():
                item.setExpanded(False)

    def keyPressEvent(self, event):
        """Overloaded method.

        This is the one place where we intercept the arrow keys, and adapt the
        interaction with the tree widget.
        """
        # pylint: disable=invalid-name
        # If one of the active key for the parent browser is pressed, we want
        # to signal it to the parent.
        if event.key() in ProgramBrowser.VALID_KEYS:
            self.key_pressed.emit()
        # If we click the EXPAND button and the node is a leaf, then we do
        # want to display the current poster, and we emit the corresponding signal.
        if event.key() == BrowserKeyMap.EXPAND and self.currentItem().parent() is not None:
            self.poster_selected.emit()
        # If key-press events are enabled, we just forward the thing to the base class
        # and then return.
        if self.__key_press_events_enabled:
            super().keyPressEvent(event)
            return
        # Otherwise we process the remaining possibility in place.
        if event.key() == BrowserKeyMap.COLLAPSE:
            self.treeview_selected.emit()



class BrowserStatus(Enum):

    """Status of the browser finite-state machine.
    """

    TREE_VIEW = auto()
    POSTER_VIEW = auto()
    CAROUSEL = auto()



class ProgramBrowser(DisplayWindowBase):

    """Poster browser.
    """

    VALID_KEYS = [key.value for key in BrowserKeyMap]
    DISPLAY_TYPE = 'Program browser'

    def __init__(self, **kwargs):
        """Constructor.
        """
        super().__init__(**kwargs)
        # Hide the header and the poster label, and show the tree view, instead.
        self.header.set_subtitle(self.DISPLAY_TYPE)
        self.poster_label.hide()
        self.tree_widget = ProgramTreeWidget(self.poster_width, screen_id=False)
        self.tree_widget.itemExpanded.connect(self.tree_widget.collapse_unused)
        self.layout().addWidget(self.tree_widget, 1, 0, 1, 3)
        self.__status = BrowserStatus.TREE_VIEW
        # We need a reference to the current poster so that we can free up the
        # memory taken by the pixmaps when the tree view is restored.
        self.__current_poster = None
        # Load the program.
        self._load_program()
        # Setup the timers. We have two of them---one for the carousel progression
        # and another one for toggling between the different views.
        self.carousel_timer = QtCore.QTimer()
        self.carousel_timer.setInterval(self.sec_to_msec(kwargs['advance_interval']))
        self.carousel_timer.timeout.connect(self.display_random_poster)
        self.toggle_timer = QtCore.QTimer()
        self.toggle_timer.setInterval(self.sec_to_msec(kwargs['pause_interval']))
        # Setup the necessary connections.
        self.toggle_timer.timeout.connect(self.toggle_view)
        self.tree_widget.poster_selected.connect(self.display_current_poster)
        self.tree_widget.treeview_selected.connect(self.display_tree_view)
        self.tree_widget.key_pressed.connect(self.toggle_timer.start)
        # By default we start the carousel.
        self.start_carousel()
        # Show the window.
        self._show()

    def _load_program(self):
        """Load the program into the tree viewer.
        """
        items = []
        for session in self.program.session_dict.values():
            item = QtWidgets.QTreeWidgetItem([session.title])
            for poster in session.posters:
                # TODO: fixme.
                #if self.program.missing_poster_image(poster.friendly_id):
                #    continue
                presenter = poster.presenter
                affiliation = presenter.affiliation
                if pd.isna(affiliation):
                    affiliation = 'N/A'
                label = f'[{poster.friendly_id}] {poster.title}'
                #if self.program.missing_poster_image(poster.friendly_id):
                #    label = f'{label} (?)'
                values = [label, presenter.full_name()]
                child = QtWidgets.QTreeWidgetItem(values)
                child.poster = poster
                item.addChild(child)
            items.append(item)
        self.tree_widget.insertTopLevelItems(0, items)

    def status_message(self):
        """Overloaded method.
        """
        if self.__status == BrowserStatus.CAROUSEL:
            delta = self.remaining_time(self.carousel_timer)
            tip = 'press any key to see the full program'
            return f'Carousel running, next random poster in {delta} s ({tip})...'
        if self.__status == BrowserStatus.TREE_VIEW:
            delta = self.remaining_time(self.toggle_timer)
            tip = 'use the arrows to navigate the tree view'
            return f'Full program view, returning to carousel in {delta} s ({tip})...'
        if self.__status == BrowserStatus.POSTER_VIEW:
            delta = self.remaining_time(self.toggle_timer)
            tip = 'left button to go back, pause button to reset the timer, up/down to navigate'
            return f'Poster view, returning to full program in {delta} s ({tip})...'
        return None

    def unload_current_pixmaps(self):
        """Unload all the pixmaps for the current poster.
        """
        if self.__current_poster is not None:
            self.__current_poster.unload_pixmaps()
            self.__current_poster = None

    def _display_poster(self, poster):
        """Base function to display a poster.
        """
        # Hide the custom tree widget and disable the key-press events.
        self.tree_widget.hide()
        self.tree_widget.disable_key_press_events()
        # Update the widgets and show the poster label.
        self.header.set_poster(poster)
        self.poster_label.setPixmap(poster.poster_pixmap(self.program.root_dir))
        self.poster_label.show()
        self.header.show()
        # Final bookkeeping.
        self.__current_poster = poster
        self.header_timer.start()
        self.toggle_timer.start()
        #self.update_debug_label()
        # And mind we need to get the focus on the main window, otherwise we might
        # be messing around with the underlying tree widget and, even more
        # important, we will not be accepting keyPressEvents.
        self.setFocus()

    def display_current_poster(self):
        """Display the poster corresponding to the current item.
        """
        self.__status = BrowserStatus.POSTER_VIEW
        self._display_poster(self.tree_widget.currentItem().poster)

    def display_random_poster(self):
        """Display a randomly chosen poster.
        """
        self._display_poster(self.program.random_poster())

    def display_next_poster(self):
        """Display the next poster in the program.
        """
        session = self.__current_poster.session
        index = (session.posters.index(self.__current_poster) + 1) % len(session.posters)
        self._display_poster(session.posters[index])

    def display_previous_poster(self):
        """Display the previous poster in the program.
        """
        session = self.__current_poster.session
        index = (session.posters.index(self.__current_poster) - 1) % len(session.posters)
        self._display_poster(session.posters[index])

    def toggle_view(self):
        """Toggle between the different views.
        """
        if self.__status == BrowserStatus.TREE_VIEW:
            self.start_carousel()
        elif self.__status == BrowserStatus.POSTER_VIEW:
            self.display_tree_view()

    def display_tree_view(self):
        """Display the tree view.
        """
        self.__status = BrowserStatus.TREE_VIEW
        # Stop the carousel timer and start the toggle timer.
        self.carousel_timer.stop()
        self.toggle_timer.start()
        # Clear up and hide the poster
        self.header.clear()
        self.poster_label.clear()
        self.poster_label.hide()
        # Show up the tree widget and re-enable the key-press events.
        self.tree_widget.show()
        self.tree_widget.enable_key_press_events()
        self.tree_widget.setFocus()
        # When we enter the tree view from the poster view, we want to make sure
        # that the selected entry in the corresponding widget is corresponding
        # to the last poster that we have seen.
        try:
            selected_poster = self.tree_widget.currentItem().poster
        except AttributeError:
            return
        if self.__current_poster is not None and selected_poster != self.__current_poster:
            parent = self.tree_widget.currentItem().parent()
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.poster == self.__current_poster:
                    self.tree_widget.setCurrentItem(item)
                    break

    def start_carousel(self):
        """Start the carousel.
        """
        # Set the status to BrowserStatus.CAROUSEL.
        self.__status = BrowserStatus.CAROUSEL
        # Stop the toggle timer.
        self.toggle_timer.stop()
        # Display the first random poster, and start the carousel timer, so that
        # the posters start cycling.
        self.display_random_poster()
        self.carousel_timer.start()

    def keyPressEvent(self, event):
        """Handle the return key button press.
        """
        # pylint: disable=invalid-name
        key = event.key()
        # If we are in carousel mode we want to switch to tree view if any key is
        # pressed.
        if self.__status == BrowserStatus.CAROUSEL and key in self.VALID_KEYS:
            self.display_tree_view()
        # If we are in tree view, we restart the toggle timer if any key is pressed.
        elif self.__status == BrowserStatus.TREE_VIEW and key in self.VALID_KEYS:
            #if key == BrowserKeyMap.COLLAPSE:
            #    self.start_carousel()
            #else:
            self.toggle_timer.start()
        # If we are in poster view mode, we buy more time with the pause button,
        # or go back to the tree view with the collapse button.
        elif self.__status == BrowserStatus.POSTER_VIEW:
            if key == BrowserKeyMap.PAUSE:
                self.toggle_timer.start()
            elif key == BrowserKeyMap.COLLAPSE:
                self.display_tree_view()
            elif key == BrowserKeyMap.ADVANCE:
                self.display_next_poster()
            elif key == BrowserKeyMap.BACKUP:
                self.display_previous_poster()



class SessionDirectory(DisplayWindowBase):

    """Session directory.
    """

    DISPLAY_TYPE = 'Program directory'

    def __init__(self, **kwargs):
        """Constructor.
        """
        super().__init__(**kwargs)
        self.advance_interval = self.sec_to_msec(kwargs['advance_interval'])
        subtitle = f'{self.DISPLAY_TYPE}'
        self.header.set_subtitle(subtitle)
        self.poster_label.hide()
        self.tree_widget = ProgramTreeWidget(self.poster_width, screen_id=True)
        self.layout().addWidget(self.tree_widget, 1, 0, 1, 3)
        # Setup the timers.
        self.toggle_timer = QtCore.QTimer()
        self.toggle_timer.setInterval(self.advance_interval)
        self.toggle_timer.timeout.connect(self.toggle_session)
        self.header_timer.start()
        self.reload_timer = QtCore.QTimer()
        self.reload_timer.setInterval(10000)
        self.reload_timer.timeout.connect(self._check_reload)
        self._reload_due = None
        # Load the program
        self.__num_sessions = self._load_program()
        self.__current_index = -1

        #if self.__num_sessions > 1:
        #    self.toggle_timer.start()
        #else:
        #    self.header_timer.stop()
        #self.toggle_session()

        self.header_timer.stop()
        self.reload_timer.start()
        self.expand_all()
        self._show()

    def _check_reload(self):
        """
        """
        logger.debug('Checking if directory needs to be reloaded.')
        if read_magic_file() or (self._reload_due is not None and datetime.datetime.now() > self._reload_due):
            self.__num_sessions = self._load_program()
            self.__current_index = -1
            self.expand_all()

    def _load_program(self):
        """Load the program.
        """
        self._reload_due = None
        self.tree_widget.clear()
        items = []
        for session in self.program.ongoing_sessions():
            end = session.end_datetime
            if self._reload_due is None or end < self._reload_due:
                self._reload_due = end
            item = QtWidgets.QTreeWidgetItem([session.title])
            for poster in session.posters:
                presenter = poster.presenter
                affiliation = presenter.affiliation
                if pd.isna(affiliation):
                    affiliation = 'N/A'
                values = [f'[{poster.friendly_id}] {poster.title}', presenter.full_name(),
                    f'{poster.screen_id}']
                child = QtWidgets.QTreeWidgetItem(values)
                child.poster = poster
                item.addChild(child)
            items.append(item)
        self.tree_widget.insertTopLevelItems(0, items)
        logger.info(f'Reload due on {self._reload_due}')
        return len(items)

    def expand_all(self):
        """Expand all the items in the program tree.
        """
        for i in range(self.__num_sessions):
            item = self.tree_widget.topLevelItem(i)
            item.setExpanded(True)

    def toggle_session(self):
        """Toggle the section being displayed.
        """
        self.__current_index = (self.__current_index + 1) % self.__num_sessions
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(index)
            item.setExpanded(index == self.__current_index)

    def status_message(self):
        """Do nothing overloaded method.
        """
        return f'Toggling session in {self.remaining_time(self.toggle_timer)} s (we appreciate your patience)...'
