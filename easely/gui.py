# Copyright (C) 2021, luca.baldini@pi.infn.it
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

This module contains all the widgets that are relevant for the slideshow.
"""

import datetime
from enum import Enum, IntEnum, auto
import os
import time

import pandas as pd
# pylint: disable=no-name-in-module, too-many-instance-attributes
from PyQt5.QtWidgets import QLabel, QGridLayout, QWidget, QGraphicsOpacityEffect,\
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem
from PyQt5.QtGui import QKeyEvent, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from pisameet import logger, abort, read_screen_id, read_magic_file
from pisameet.profile import psstatus
from pisameet.program import Poster, PosterRoster, PosterProgram, DATE_FORMAT,\
    DATE_PRETTY_FORMAT, DATETIME_FORMAT



class FadingEffect(QGraphicsOpacityEffect):

    """Graphic effect for picture fade-in/out.

    This is simple graphic effect allowing a fade-in/out effect to a gradual
    change in the opacity. Internally, the transitions are controlled via a
    QTimer() object increasing or decreasing the opacity by a fixed amount
    (the _step class member) at each timeout.

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
        self._timer = QTimer()
        self._timer.start(self._interval)
        logger.debug('Opacity fade time set to %.3f s', self.fade_time())

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
            self._timer.disconnect()
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
            self._timer.disconnect()
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



class RosterTable(QTableWidget):

    """Custom QTableWidget to display a poster roster.

    In addition to the basic functionality of the base class, this is designed
    to highlight one row at a time (e.g., by setting a different color) in
    order to visually indicate the poster being displayed at any given time.

    Arguments
    ---------
    row_height : int
        The height of each row in the table.

    default_rgb : int
        The default value of the three RGB channels for the default
        (i.e., not highlighted) color.
    """

    def __init__(self, height: int, row_height: int = 26,
        default_rgb: int = 175):
        """Constructor,
        """
        super().__init__()
        self.setColumnCount(3)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setMinimumSectionSize(row_height)
        self.verticalHeader().setDefaultSectionSize(row_height)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setShowGrid(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setStyleSheet("border: 0px")
        self.setEnabled(False)
        self.setMaximumHeight(height)
        self._default_color = QColor(default_rgb, default_rgb, default_rgb)
        self._highlight_color = QColor(0, 0, 0)
        self._highlighted_row = None

    def set_text(self, row: int, col: int, text: str):
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
        item = QTableWidgetItem(text)
        item.setForeground(self._default_color)
        self.setItem(row, col, item)

    def set_poster(self, row: int, poster: Poster, title_length=65):
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

    def set_roster(self, roster: PosterRoster):
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

    def set_current_row(self, row: int):
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



class ScreenHeaderMinimal(QWidget):

    """Minimal screen header.

    This is a composite object including:

    * a QLabel object for the title (typically, the conference name and location);
    * a QLabel object for the subtitle (e.g., indicating the session);
    * a QLabel object for a status message.
    """

    def __init__(self, title: str, *args, **kwargs):
        """Constructor.
        """
        title_font_size = kwargs.get('title_font_size', 20)
        subtitle_font_size = kwargs.get('subtitle_font_size', 18)
        bottom_row_height = kwargs.get('bottom_row_height', 15)
        horizontal_spacing = kwargs.get('horizontal_spacing', 30)
        vertical_spacing = kwargs.get('vertical_spacing', 8)
        margin = kwargs.get('margin', 0)
        super().__init__()
        self.setLayout(QGridLayout())
        self.layout().setHorizontalSpacing(horizontal_spacing)
        self.layout().setVerticalSpacing(vertical_spacing)
        self.layout().setContentsMargins(margin, margin, margin, margin)
        # Create all the necessary widgets: the title Qlabel...
        self.title_label = QLabel()
        font = self.title_label.font()
        font.setPointSize(title_font_size)
        self.title_label.setFont(font)
        self.title_label.setText(title)
        # ... the subtitle QLabel...
        self.subtitle_label = QLabel()
        font = self.subtitle_label.font()
        font.setPointSize(subtitle_font_size)
        self.subtitle_label.setFont(font)
        # ... and the status message label.
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignTop)
        # Setup the payout.
        self._setup_layout()
        # And freeze the height of the last column to add a minimum space between
        # the header and the actual content.
        self.layout().setRowMinimumHeight(self.layout().columnCount(), bottom_row_height)

    def _setup_layout(self):
        """Setup the layout.
        """
        self.layout().addWidget(self.title_label, 0, 0, 1, 3)
        self.layout().addWidget(self.subtitle_label, 1, 0, 1, 3)
        self.layout().addWidget(self.status_label, 2, 0, 1, 3)

    def set_subtitle(self, text):
        """Set the subtitle.
        """
        self.subtitle_label.setText(text)

    def set_status(self, text):
        """Set the status text label.
        """
        text = f'<font color="white" size="4">F</font><br/>'\
               f'<font color="black" size="2">{text}</font><br/>'
        self.status_label.setText(text)

    def clear(self):
        """Clear the header.
        """
        self.status_label.setText('')



class ScreenHeader(ScreenHeaderMinimal):

    """Fully fledged poster header.

    This is a composite object that can be used as a generic header for
    different kinds of displays. More specifically, it includes:

    * a QLabel object for the title (typically, the conference name and location);
    * a QLabel object for the subtitle (e.g., indicating the session);
    * a Qlabel object for the presenter pic;
    * a QLabel object for the QR code pointing at the indico page of the poster;
    * a QLabel object holding the name and affiliation of the presenter;
    * a RosterTable object for the list of posters;
    * a QLabel object for a status message.
    """

    def __init__(self, title: str, height: int, portrait_height: int, **kwargs):
        """Constructor.
        """
        # ... the presenter portrait QLabel...
        self.portrait_label = QLabel()
        self.portrait_label.setFixedSize(portrait_height, portrait_height)
        self.portrait_label.setAlignment(Qt.AlignLeft)
        # ... the QR code QLabel...
        self.qrcode_label = QLabel()
        self.qrcode_label.setFixedSize(portrait_height, portrait_height)
        self.qrcode_label.setAlignment(Qt.AlignCenter)
        # ... the presenter name/affiliation QLabel...
        self.presenter_label = QLabel()
        self.presenter_label.setWordWrap(True)
        self.presenter_label.setAlignment(Qt.AlignTop)
        # ... the poster roster table...
        self.table = RosterTable(portrait_height)
        self._roster = None
        super().__init__(title, **kwargs)
        self.setFixedHeight(height)
        if False:
            self.show_debug_borders()

    def _setup_layout(self, bottom_margin: int = 10):
        """Overloaded method.
        """
        self.layout().addWidget(self.title_label, 0, 0, 1, 3)
        self.layout().addWidget(self.subtitle_label, 1, 0, 1, 3)
        self.layout().addWidget(self.portrait_label, 2, 0)
        self.layout().addWidget(self.qrcode_label, 2, 1)
        self.layout().addWidget(self.table, 2, 2)
        self.layout().addWidget(self.presenter_label, 3, 0, 1, 2)
        self.layout().addWidget(self.status_label, 3, 2)
        self.layout().setRowMinimumHeight(self.layout().rowCount(), bottom_margin)

    def show_debug_borders(self):
        """Show the relevant widget borders to debug the geometry.
        """
        for item in (self.title_label, self.subtitle_label, self.portrait_label,
            self.qrcode_label, self.presenter_label, self.table, self.status_label):
            item.setStyleSheet('border: 1px solid black;')

    def set_roster(self, roster):
        """Set the poster roster for the table.
        """
        self._roster = roster
        self.set_subtitle(self._roster.session.title)

    def _update_pixmaps(self, poster):
        """Update the two pixmaps.
        """
        self.portrait_label.setPixmap(poster.presenter_pixmap)
        self.qrcode_label.setPixmap(poster.qrcode_pixmap)

    def _update_presenter(self, poster):
        """Update the presenter name and affiliation.
        """
        presenter = poster.presenter
        text = f'<font color="black" size="4">{presenter.full_name()}</font><br/>'\
               f'<font color="gray" size="2">{presenter.affiliation}</font><br/>'
        self.presenter_label.setText(text)

    def set_poster(self, poster):
        """Set the poster for the header.
        """
        self._update_pixmaps(poster)
        self._update_presenter(poster)
        self.table.clear()
        self.table.setRowCount(1)
        self.table.set_poster(0, poster)
        self.table.set_current_row(0)

    def update(self, current_poster_id):
        """Update the header based on the roster information and the current poster.
        """
        poster = self._roster[current_poster_id]
        self._update_pixmaps(poster)
        self._update_presenter(poster)
        self.table.set_current_row(current_poster_id)

    def clear(self):
        """Clear the header.
        """
        super().clear()
        self.presenter_label.setText('')
        self.status_label.setText('')
        self.table.clear()
        self.portrait_label.clear()
        self.qrcode_label.clear()



class DisplaWindowBase(QWidget):

    """Base class for display windows.
    """

    DISPLAY_TYPE = None

    def __init__(self, header_class=ScreenHeader, **kwargs):
        """Constructor.
        """
        super().__init__()
        self.setStyleSheet('background-color: "white"')
        window_title = kwargs['conference_name']
        if self.DISPLAY_TYPE is not None:
            window_title = f'{window_title} -- {self.DISPLAY_TYPE}'
        self.setWindowTitle(window_title)
        # Parse the command-line arguments.
        self.config_file_path = kwargs['cfgfile']
        self.display_mode = kwargs['mode']
        self.poster_width = kwargs['poster_width']
        self.header_height = kwargs['header_height']
        self.portrait_height = kwargs['portrait_height']
        # Retrieve the display date.
        display_date = kwargs.get('display_date')
        # If the --display-date command-line switch is not set we jut cache the
        # current day and time. Note that we cache both the date and the datetime
        # of the display.
        if display_date is None:
            self.display_date = None#datetime.date.today()
            self.display_datetime = None#datetime.datetime.now()
        # Otherwise we also parse the optional display time and proceed.
        else:
            display_time = kwargs.get('display_time')
            display_datetime = f'{display_date} {display_time}'
            self.display_date = datetime.datetime.strptime(display_date, DATE_FORMAT).date()
            self.display_datetime = datetime.datetime.strptime(display_datetime, DATETIME_FORMAT)
        # Setup the widget.
        self.setLayout(QGridLayout())
        self.layout().setColumnMinimumWidth(0, self.poster_width)
        header_title = f'{kwargs["conference_name"]} - {kwargs["conference_location"]} - {kwargs["conference_dates"]}'
        self.header = header_class(header_title, kwargs['header_height'], kwargs['portrait_height'])
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignHCenter or Qt.AlignTop)
        self.debug_label = QLabel()
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
        self.header_timer = QTimer()
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
        msg = f'Powered by https://github.com/lucabaldini/pisameet, {uptime:.1f} s uptime, {psstatus()}'
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
        self.header.set_status(self.status_message())

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



class SlideShow(DisplaWindowBase):

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
        self.screen_id = read_screen_id()
        self.__status = SlideShowStatus.STOPPED
        self.__current_index = 0
        # Setup the timers.
        self.advance_timer = QTimer()
        self.advance_timer.setInterval(self.advance_interval)
        self.advance_timer.timeout.connect(self.advance)
        self.resume_timer = QTimer()
        self.resume_timer.setInterval(self.pause_interval)
        self.resume_timer.setSingleShot(True)
        self.resume_timer.timeout.connect(self.resume)
        self.reload_timer = QTimer()
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
        if not self.poster_roster.session.ongoing():
            logger.info(f'Session {self.poster_roster.session} is over, reloading the program...')
            self._load_roster()
            logger.info(f'Current session: {self.poster_roster.session}')

    def _load_roster(self):
        """Load a given session from the underlying configuration file.
        """
        logger.info('Loading poster roster...')
        self.stop()
        self.hide()
        folder_path = os.path.dirname(self.config_file_path)
        self.poster_roster = PosterRoster(self.config_file_path, folder_path,
            self.screen_id, self.display_datetime)
        if len(self.poster_roster) == 0:
            logger.info('Displaying default poster...')
            self._show()
            pix1, pix2 = Poster.load_default_pixmaps(self.poster_width, self.portrait_height)
            self.poster_label.setPixmap(pix1)
            self.header.clear()
            self.header.set_subtitle('')
            self.header.qrcode_label.setPixmap(pix2)
            return
        self.poster_roster.load_pixmaps(self.poster_width, self.portrait_height)
        self.header.set_roster(self.poster_roster)
        subtitle = f'{self.poster_roster.session.title} (screen #{self.screen_id})'
        self.header.set_subtitle(subtitle)
        self.header.table.set_roster(self.poster_roster)
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
        self.poster_label.setPixmap(poster.poster_pixmap)
        self.fading_effect.fade_in()

    def advance(self) -> None:
        """Advance to the next image.
        """
        self.display_poster(self.__current_index + 1)

    def backup(self) -> None:
        """Advance to the next image.
        """
        self.display_poster(self.__current_index - 1)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Overloaded method to handle key events.
        """
        # Disengage the keyboard if there is less than two posters.
        if len(self.poster_roster) <= 1:
            return
        # pylint: disable=invalid-name
        key = event.text()
        if not key in self.VALID_KEYS:
            logger.warning('Invalid key pressed (%s).', key)
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

    EXPAND = Qt.Key_Right
    COLLAPSE = Qt.Key_Left
    ADVANCE = Qt.Key_Down
    BACKUP = Qt.Key_Up
    PAUSE = Qt.Key_Return



class ProgramTreeWidget(QTreeWidget):

    """Light wrapper over the QTreeWidget class.
    """

    # Signal emitted when any active key has been pressed.
    key_pressed = pyqtSignal()

    # Signal emitted when the display of the current poster is requested.
    poster_selected = pyqtSignal()

    # Signal emitted when the tree view uis requested.
    treeview_selected = pyqtSignal()

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



class ProgramBrowser(DisplaWindowBase):

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
        self.program = PosterProgram(kwargs.get('cfgfile'))
        self._load_program()
        # Setup the timers. We have two of them---one for the carousel progression
        # and another one for toggling between the different views.
        self.carousel_timer = QTimer()
        self.carousel_timer.setInterval(self.sec_to_msec(kwargs['advance_interval']))
        self.carousel_timer.timeout.connect(self.display_random_poster)
        self.toggle_timer = QTimer()
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
        for session, posters in self.program.items():
            item = QTreeWidgetItem([session.title])
            for poster in posters:
                if self.program.missing_poster_image(poster.friendly_id):
                    continue
                presenter = poster.presenter
                affiliation = presenter.affiliation
                if pd.isna(affiliation):
                    affiliation = 'N/A'
                label = f'[{poster.friendly_id}] {poster.title}'
                #if self.program.missing_poster_image(poster.friendly_id):
                #    label = f'{label} (?)'
                values = [label, presenter.full_name()]
                child = QTreeWidgetItem(values)
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
        # Hide the cutsom tree widget and disable the key-press events.
        self.tree_widget.hide()
        self.tree_widget.disable_key_press_events()
        # Unload the pixmaps.
        self.unload_current_pixmaps()
        # Load the necessary pixmaps for the poster.
        self.program.load_poster_pixmaps(poster, self.poster_width, self.portrait_height)
        # Update the widgets and show the poster label.
        self.header.set_poster(poster)
        if self.__status == BrowserStatus.CAROUSEL:
            self.header.set_subtitle(f'{self.DISPLAY_TYPE} (random carousel)')
        else:
            self.header.set_subtitle(f'{self.DISPLAY_TYPE} ({poster.session.title})')
        self.poster_label.setPixmap(poster.poster_pixmap)
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
        index = self.__current_poster.session_index
        self._display_poster(self.program.select_by_session_index(session, index + 1))

    def display_previous_poster(self):
        """Display the previous poster in the program.
        """
        session = self.__current_poster.session
        index = self.__current_poster.session_index
        self._display_poster(self.program.select_by_session_index(session, index - 1))

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
        self.header.set_subtitle(f'{self.DISPLAY_TYPE} (tree view)')
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



class SessionDirectory(DisplaWindowBase):

    """Session directory.
    """

    DISPLAY_TYPE = 'Poster session directory'

    def __init__(self, **kwargs):
        """Constructor.
        """
        super().__init__(header_class=ScreenHeaderMinimal, **kwargs)
        self.advance_interval = self.sec_to_msec(kwargs['advance_interval'])
        subtitle = f'{self.DISPLAY_TYPE}'
        self.header.set_subtitle(subtitle)
        self.poster_label.hide()
        self.tree_widget = ProgramTreeWidget(self.poster_width, screen_id=True)
        self.layout().addWidget(self.tree_widget, 1, 0, 1, 3)
        # Setup the timers.
        self.toggle_timer = QTimer()
        self.toggle_timer.setInterval(self.advance_interval)
        self.toggle_timer.timeout.connect(self.toggle_session)
        self.header_timer.start()
        self.reload_timer = QTimer()
        self.reload_timer.setInterval(10000)
        self.reload_timer.timeout.connect(self._check_reload)
        self._reload_due = None
        # Load the program
        self.program = PosterProgram(kwargs.get('cfgfile'))
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
        for session, posters in self.program.items():
            if not session.ongoing(self.display_datetime):
                continue
            end = session.end
            if self._reload_due is None or end < self._reload_due:
                self._reload_due = end
            item = QTreeWidgetItem([session.title])
            for poster in posters:
                presenter = poster.presenter
                affiliation = presenter.affiliation
                if pd.isna(affiliation):
                    affiliation = 'N/A'
                values = [f'[{poster.friendly_id}] {poster.title}', presenter.full_name(),
                    f'{poster.screen_id}']
                child = QTreeWidgetItem(values)
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
