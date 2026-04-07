# Copyright (C) 2024 the ipose team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Graphical user interface.
"""

from enum import Enum, auto
import math
import pathlib

from ipose import IPOSE_QSS, logger
import ipose.config
from ipose.__qt__ import QtCore, QtGui, QtWidgets


_DEFAULT_STYLESHEET = IPOSE_QSS / 'default.qss'


class ResizePolicy(Enum):

    """Enum class for the ``QPixmap`` resize policy.

    In most of the cases we want to resize rastered images to their final dimensions
    beforehand and display them onto  a ``QLabel`` without any additional manipulation,
    in order to (i) optimize the whole process for speed and resources; and (ii)
    take advantage of the higher quality of the resizing algorithms that are available
    offline. This ``Enum`` class provide the necessary granularity to ensure that
    images are displayed at the best possible resolution.
    """

    #: Do not attempt to resize the image, and place the row bitmap onto the display.
    DO_NOT_RESIZE = auto()
    #: Make sure the image width matches that of the canvas and do nothing.
    MATCH_WIDTH = auto()
    #: Make sure the image height matches that of the canvas and do nothing.
    MATCH_HEIGHT = auto()
    #: Make sure the image size matches that of the canvas and do nothing.
    MATCH_SIZE = auto()
    #: Scale the image to the width of the target image, preserving the aspect ratio.
    SCALE_TO_WIDTH = auto()
    #: Scale the image to the height of the target image, preserving the aspect ratio.
    SCALE_TO_HEIGHT = auto()
    #: Scale the image to the size of the target image, when the aspect ratio allows.
    SCALE_TO_SIZE = auto()



class Canvas(QtWidgets.QLabel):

    """Simple wrapper around the ``QtWidgets.QLabel`` class representing a widget
    to display a picture, be that the actual poster, a logo, a close-up picture
    of the presenter or a qrcode.

    Parameters
    ----------
    parent
        The parent widget.

    width
        The width of the canvas (if set, this is frozen for the entire lifetime
        of the object).

    height
        The height of the canvas (if set, this is frozen for the entire lifetime
        of the object).
    """

    #: Default tranformation for scaling rastered images (highest quality).
    _DEFAULT_TRANSFORM = QtCore.Qt.TransformationMode.SmoothTransformation

    def __init__(self, parent: QtWidgets.QWidget = None, width: int = None,
        height: int = None) -> None:
        """Constructor.
        """
        super().__init__(parent)
        if width is not None:
            self.setFixedWidth(width)
        if height is not None:
            self.setFixedHeight(height)

    @staticmethod
    def scale_to_width(pixmap: QtGui.QPixmap, width: int,
        transform: QtCore.Qt.TransformationMode = _DEFAULT_TRANSFORM) -> QtGui.QPixmap:
        """Scale a given ``QtGui.QPixmap`` object to a target width.

        Parameters
        ----------
        pixmap
            The original ``QtGui.QPixmap`` object.

        width
            The target width in pixels.

        transform
            The scaling algorithm.

        Returns
        -------
        QtGui.QPixmap
            The resized ``QPixmap`` object.
        """
        if pixmap.width() == width:
            return pixmap
        logger.debug(f'Resizing pixmap to width ({pixmap.width()} -> {width})...')
        return pixmap.scaledToWidth(width, transform)

    @staticmethod
    def scale_to_height(pixmap: QtGui.QPixmap, height: int,
        transform: QtCore.Qt.TransformationMode = _DEFAULT_TRANSFORM) -> QtGui.QPixmap:
        """Scale a given ``QtGui.QPixmap`` object to a target height.

        Parameters
        ----------
        pixmap
            The original ``QtGui.QPixmap`` object.

        height
            The target height in pixels.

        transform
            The scaling algorithm.

        Returns
        -------
        QtGui.QPixmap
            The resized ``QPixmap`` object.
        """
        if pixmap.height() == height:
            return pixmap
        logger.debug(f'Resizing pixmap to height ({pixmap.height()} -> {height})...')
        return pixmap.scaledToHeight(height, transform)

    @staticmethod
    def scale_to_size(pixmap: QtGui.QPixmap, width: int, height: int,
        transform: QtCore.Qt.TransformationMode = _DEFAULT_TRANSFORM) -> QtGui.QPixmap:
        """Scale a given ``QtGui.QPixmap`` object to a target size.

        This raises a ``RuntimeError`` when the aspect ration of the image does
        not match that of the target canvas.

        Parameters
        ----------
        pixmap
            The original ``QtGui.QPixmap`` object.

        width
            The target width in pixels.

        height
            The target height in pixels.

        transform
            The scaling algorithm.

        Returns
        -------
        QtGui.QPixmap
            The resized ``QPixmap`` object.
        """
        source_aspect_ratio = pixmap.width() / pixmap.height()
        target_aspect_ratio = width / height
        # If there is a mismatch in the aspect ratio we give up...
        if not math.isclose(source_aspect_ratio, target_aspect_ratio):
            raise RuntimeError(f'Mismatch in aspect ratio ({source_aspect_ratio} vs '
                f'{target_aspect_ratio}) while painting a canvas')
        # ... and otherwise we can equivalently rescale to either the width or the
        # height of the canvas.
        return Canvas.scale_to_width(pixmap, width, transform)

    def paint(self, source: str | pathlib.Path | QtGui.QPixmap,
        resize_policy: ResizePolicy = ResizePolicy.DO_NOT_RESIZE,
        transform: QtCore.Qt.TransformationMode = _DEFAULT_TRANSFORM) -> None:
        """Paint a given image on the canvas.

        Parameters
        ----------
        source
            The source of the rastered image to be painted, that can be either the
            path to an image file or a ``QPixmap`` object, in case we want to read
            the file once and cache the image for multiple uses.

        resize_policy
            The resize policy, see :class:`ResizePolicy`.

        transform
            The resize algorithm to be used, when relevant.
        """
        if not isinstance(source, QtGui.QPixmap):
            source = QtGui.QPixmap(f'{source}')
        if resize_policy == ResizePolicy.MATCH_WIDTH:
            if source.width() != self.width():
                raise RuntimeError(f'QPixmap width does match canvas '
                    f'({source.width()} vs {self.width()})')
        elif resize_policy == ResizePolicy.MATCH_HEIGHT:
            if source.height() != self.height():
                raise RuntimeError(f'QPixmap height does match canvas '
                    f'({source.height()} vs {self.height()})')
        elif resize_policy == ResizePolicy.MATCH_SIZE:
            source_size = source.width(), source.height()
            canvas_size = self.width(), self.height()
            if source_size != canvas_size:
                raise RuntimeError(f'QPixmap size does match canvas '
                    f'({source_size} vs {canvas_size})')
        elif resize_policy == ResizePolicy.SCALE_TO_WIDTH:
            source = self.scale_to_width(source, self.width(), transform)
        elif resize_policy == ResizePolicy.SCALE_TO_HEIGHT:
            source = self.scale_to_height(source, self.height(), transform)
        elif resize_policy == ResizePolicy.SCALE_TO_SIZE:
            source = self.scale_to_size(source, self.width(), self.height(), transform)
        self.setPixmap(source)



class LayoutFrame(QtWidgets.QFrame):

    """Base class for all the GUI widgets.

    This is supposed to act as a base class for all the widgets in the graphical
    user interface, and encapsulates some useful methods that can then easily
    reused downstream.

    Any LayoutFrame object comes equipped with a QGridLayout that can be used to
    add other widgets.

    Parameters
    ----------
    parent
        The parent widget.
    """

    def __init__(self, parent: QtWidgets.QWidget = None, margins: int = 0) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self.setLayout(QtWidgets.QGridLayout(self))
        self.layout().setContentsMargins(margins, margins, margins, margins)

    def add_widget(self, widget: QtWidgets.QWidget, row: int, column: int,
        row_span: int = 1, column_span: int = 1, object_name: str = None) -> QtWidgets.QWidget:
        """Add a widget to the underlying QGridLayout object.
        """
        if ipose.config.get('gui.debug'):
            widget.setStyleSheet("border: 1px solid black;")
        self.layout().addWidget(widget, row, column, row_span, column_span)
        if object_name is not None:
            widget.setObjectName(object_name)
        return widget

    def add_text_label(self, row: int, column: int, row_span: int = 1,
        column_span: int = 1, object_name: str = None) -> QtWidgets.QLabel:
        """Add a text label to the underlying QGridLayout object.
        """
        label = QtWidgets.QLabel(self)
        return self.add_widget(label, row, column, row_span, column_span, object_name)

    def add_canvas(self, row: int, column: int, row_span: int = 1, column_span: int = 1,
        width: int = None, height: int = None, object_name: str = None) -> QtWidgets.QLabel:
        """Add a picture label to the underlying QGridLayout object.
        """
        canvas = Canvas(self, width, height)
        return self.add_widget(canvas, row, column, row_span, column_span, object_name)



class Header(LayoutFrame):

    """The screen header.
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self.layout().setColumnStretch(0, 1)
        self.title_label = self.add_text_label(0, 0, object_name='title')
        self.subtitle_label = self.add_text_label(1, 0, object_name='subtitle')
        self.logo_canvas = self.add_canvas(0, 1, 3, height=ipose.config.get('gui.header.height'))

    def set_title(self, text: str) -> None:
        """Set the subtitle.
        """
        self.title_label.setText(text)

    def set_subtitle(self, text: str) -> None:
        """Set the subtitle.
        """
        self.subtitle_label.setText(text)

    def set_logo(self, file_path: str | pathlib.Path) -> None:
        """
        """
        self.logo_canvas.paint(file_path, ResizePolicy.SCALE_TO_HEIGHT)



class RosterTable(LayoutFrame):

    """
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        #height = 200
        super().__init__(parent)
        #self.setFixedHeight(height)



class PosterBanner(LayoutFrame):

    """A banner encapsulating all the poster information (presenter, title, qr code
    and alike).
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        size = ipose.config.get('gui.banner.pic_size')
        super().__init__(parent)
        self.portrait_canvas = self.add_canvas(0, 0, 1, 1, *size)
        self.qrcode_canvas = self.add_canvas(0, 1, 1, 1, *size)
        self.roster_table = self.add_widget(RosterTable(self), 0, 2, 2)
        self.name_label = self.add_text_label(1, 0, 1, 2, object_name='name')
        self.affiliation_label = self.add_text_label(2, 0, 1, 2, object_name='affiliation')
        self.status_label = self.add_text_label(2, 2, object_name='message')

    def set_portrait(self, source: str | pathlib.Path | QtGui.QPixmap) -> None:
        """
        """
        self.portrait_canvas.paint(source, ResizePolicy.MATCH_SIZE)

    def set_qrcode(self, source: str | pathlib.Path | QtGui.QPixmap) -> None:
        """
        """
        self.qrcode_canvas.paint(source, ResizePolicy.MATCH_SIZE)

    def set_presenter(self, name: str, affiliation: str) -> None:
        """
        """
        self.name_label.setText(name)
        self.affiliation_label.setText(affiliation)

    def set_status(self, text: str) -> None:
        """
        """
        self.status_label.setText(text)



class PosterCanvas(LayoutFrame):

    """
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        width = ipose.config.get('gui.poster.width')
        super().__init__(parent)
        self.poster_canvas = self.add_canvas(0, 0, width=width)
        self.layout().setColumnMinimumWidth(0, width)



class Footer(LayoutFrame):

    """The screen footer.
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self.message_label = self.add_text_label(0, 0, object_name='message')
        self.setFixedHeight(ipose.config.get('gui.footer.height'))

    def set_message(self, text: str) -> None:
        """Set the subtitle.
        """
        self.message_label.setText(text)



class DisplayWindow(LayoutFrame):

    """
    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Constructor.
        """
        super().__init__(parent)
        self.header = self.add_widget(Header(self), 0, 1, object_name='header')
        self.banner = self.add_widget(PosterBanner(self), 1, 1, object_name='banner')
        self.canvas = self.add_widget(PosterCanvas(self), 2, 1, object_name='canvas')
        self.footer = self.add_widget(Footer(self), 3, 1, object_name='footer')
        self.layout().setRowStretch(2, 1)
        self.layout().setColumnMinimumWidth(0, 10)
        self.layout().setColumnMinimumWidth(3, 10)
        self.layout().setColumnStretch(0, 1)
        self.layout().setColumnStretch(3, 1)


def bootstrap_qapplication() -> QtWidgets.QApplication:
    """Create a QApplication object and apply the proper stypesheet.
    """
    #pylint: disable=unspecified-encoding
    stylesheet = ipose.config.get('gui.stylesheet')
    if stylesheet is None:
        stylesheet = _DEFAULT_STYLESHEET
    qapp = QtWidgets.QApplication(sys.argv)
    logger.info(f'Applying stylesheet {stylesheet} to the main application...')
    with open(stylesheet, 'r') as stylesheet:
        qapp.setStyleSheet(stylesheet.read())
    return qapp



if __name__ == '__main__':
    import sys
    from ipose import IPOSE_TEST_DATA
    from ipose.__qt__ import exec_qapp
    app = bootstrap_qapplication()
    #print(QtGui.QFontDatabase.families())
    #ipose.config.set('gui.debug', True)
    window = DisplayWindow()
    window.header.set_title('First Topical Conference on Something Very Interesting')
    window.header.set_subtitle('Once Upon a time, in a far, far away land...')
    window.header.set_logo(IPOSE_TEST_DATA / 'ipose_logo_white.png')
    window.footer.set_message('And this is a debug message...')
    window.banner.set_portrait(IPOSE_TEST_DATA / 'mona_lisa_crop.png')
    window.banner.set_qrcode(IPOSE_TEST_DATA / 'ipose_qrcode.png')
    window.banner.set_presenter('Monna Lisa', 'Gherardini Family (Florence)')
    window.canvas.poster_canvas.paint(IPOSE_TEST_DATA / 'leonardo.png', ResizePolicy.MATCH_WIDTH)
    window.banner.set_status('Status messages will be displayed in this box...')
    window.show()
    exec_qapp(app)
