# Copyright (C) 2026, the easely team.
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


"""Convenience module handling the Qt-related import.
"""

import sys

from loguru import logger
from PyQt5 import QtCore, QtGui, QtWidgets


def exec_qapp(qapp: QtWidgets.QApplication) -> int:
    """QApplication bootstrap call (with the final underscore).

    This small wrapper is intended to make the transition from and to PyQt5/6 and/or
    PySide2/6 easier (the QApplication main loop is entered with `exec_()` in the
    first case and `exec()` in the second).
    """
    return sys.exit(qapp.exec_())


def bootstrap_window(WindowClass: type, padding: int=20, **kwargs) -> QtWidgets.QApplication:
    """Bootstrap the poster application.

    This is a small helper function to automate a series of operations that are
    common to all the main windows of the framework. In a nutshell, it creates a
    QApplication, determines the appropriate poster width from the screen size (unless
    this is explicitly overridden via command-line options), instantiates the main window
    class, and finally enters the main loop of the application.

    Arguments
    ---------
    WindowClass
        The class of the main window to instantiate.

    padding
        The amount of horizontal padding to subtract from the screen width.

    Returns
    -------
    QtWidgets.QApplication
        The application instance.
    """
    app = QtWidgets.QApplication(sys.argv)
    if kwargs.get("poster_width") is None:
        poster_width = app.screens()[0].size().width() - padding
        logger.info(f"Setting poster width to {poster_width} (based on the screen size)")
        kwargs["poster_width"] = poster_width
    _ = WindowClass(**kwargs)
    return exec_qapp(app)
