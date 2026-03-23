#!/usr/bin/env python3
#
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

"""Main slideshow application.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from PyQt5.QtWidgets import QApplication

from pisameet import logger
from pisameet.gui import ProgramBrowser
from pisameet.options import ArgumentParser



PARSER = ArgumentParser()
PARSER.add_geometry()
PARSER.add_pause()
PARSER.add_advance()



if __name__ == '__main__':
    args = PARSER.parse_args()
    app = QApplication(sys.argv)
    kwargs = args.__dict__
    # Determine the appropriate poster width from the screen size unless this is
    # explicitly overridden via command-line options.
    if kwargs.get('poster_width') is None:
        poster_width = app.screens()[0].size().width() - 20
        logger.info('Setting posted width to %d (based on the screen size)', poster_width)
        kwargs['poster_width'] = poster_width
    browser = ProgramBrowser(**kwargs)
    sys.exit(app.exec_())
