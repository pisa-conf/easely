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

"""Command-line options.
"""


import argparse
from enum import Enum
import os

from pisameet import PISAMEET_BASE


class DisplayMode(Enum):

    """Definition of the possible visualization modes for the applications.
    """

    DEFAULT = 'default'
    MAXIMIZE = 'maximize'
    FULLSCREEN = 'fullscreen'



VALID_DISPLAY_MODES = [mode.value for mode in DisplayMode]



class ArgumentFormatter(argparse.RawDescriptionHelpFormatter,
                        argparse.ArgumentDefaultsHelpFormatter):

    """Do nothing class combining our favorite formatting for the
    command-line options, i.e., the newlines in the descriptions are
    preserved and, at the same time, the argument defaults are printed
    out when the --help options is passed.

    The inspiration for this is coming from one of the comments in
    https://stackoverflow.com/questions/3853722
    """

    pass



class ArgumentParser(argparse.ArgumentParser):

    """Light-weight wrapper over the argparse ArgumentParser class.

    This is mainly intended to reduce boilerplate code and guarantee a minimum
    uniformity in terms of how the command-line options are expressed across
    different applications.
    """

    def __init__(self, prog=None, usage=None, description=None):
        """Constructor.
        """
        argparse.ArgumentParser.__init__(self, prog, usage, description,
            formatter_class=ArgumentFormatter)
        self.add_argument('cfgfile', type=str,
            help='path to the input excel configuration file')
        self.add_argument('--conference-name', type=str, default='16th Pisa Meeting on Advanced Detectors',
            help='the conference name')
        self.add_argument('--conference-dates', type=str, default='La Biodola, Isola d\'Elba',
            help='the conference dates')
        self.add_argument('--conference-location', type=str, default='May 26-June 1, 2024',
            help='the conference location')

    def add_geometry(self, default_header_height=310):
        """Add all the geometry options.
        """
        self.add_argument('--mode', type=str, default='fullscreen', choices=VALID_DISPLAY_MODES,
            help='display geometry')
        self.add_argument('--poster-width', type=int, default=None,
            help='width of the poster display (taken from the screen size by default)')
        self.add_argument('--header-height', type=int, default=default_header_height,
            help='height of the poster header')
        self.add_argument('--portrait-height', type=int, default=132,
            help='height of the presenter portraits and QR codes')

    def add_datetime(self):
        """Add an option to fake a different running date.
        """
        self.add_argument('--display-date', type=str, default=None,
            help='optional date, e.g., 23/05/2022')
        self.add_argument('--display-time', type=str, default='12:00',
            help='optional time, e.g., 12:00')


    def add_pause(self, default=300.):
        """Add the pause interval option.
        """
        self.add_argument('--pause-interval', type=float, default=default,
             help='pause time interval [s]')

    def add_advance(self, default=30.):
        """Add the advance interval option.
        """
        self.add_argument('--advance-interval', type=float, default=default,
             help='pause time interval [s]')

    def add_fading(self):
        """Add the fading effect option.
        """
        self.add_argument('--fading', action='store_true',
            help='enable the fading effect between posters')
        self.add_argument('--no-fading', action='store_false',
            help='disable the fading effect between posters')
        self.set_defaults(fading=False)
