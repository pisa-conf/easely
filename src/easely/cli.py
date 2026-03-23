# Copyright (C) 2026, the easely team.
#
# For the license terms see the file LICENSE, distributed along with this
# software.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Main command-line interface.
"""

import argparse
import sys
from enum import Enum

from loguru import logger
from PyQt5.QtWidgets import QApplication

from easely import __name__ as __package_name__
from easely import __version__
from easely import logging_
from easely.gui import PosterProgram, ProgramBrowser, SessionDirectory, SlideShow


def start_message() -> None:
    """Print the start message.
    """
    msg = f"""
    This is {__package_name__} version {__version__}.

    Copyright (C) 2022--2026, the {__package_name__} team.

    {__package_name__} comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it under certain
    conditions. See the LICENSE file for details.

    Visit https://github.com/lucabaldini/{__package_name__} for more information.
    """
    print(msg)


class _Formatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):

    """Do nothing class combining our favorite formatting for the
    command-line options, i.e., the newlines in the descriptions are
    preserved and, at the same time, the argument defaults are printed
    out when the --help options is passed.

    The inspiration for this is coming from one of the comments in
    https://stackoverflow.com/questions/3853722
    """


class DisplayMode(Enum):

    """Definition of the possible visualization modes for the applications.
    """

    DEFAULT = 'default'
    MAXIMIZE = 'maximize'
    FULLSCREEN = 'fullscreen'


VALID_DISPLAY_MODES = [mode.value for mode in DisplayMode]


class CliArgumentParser(argparse.ArgumentParser):

    """Application-wide argument parser.
    """

    _DESCRIPTION = None
    _EPILOG = None
    _FORMATTER_CLASS = _Formatter

    def __init__(self) -> None:
        """Overloaded method.
        """
        super().__init__(description=self._DESCRIPTION, epilog=self._EPILOG,
                         formatter_class=self._FORMATTER_CLASS)
        subparsers = self.add_subparsers(required=True, help="sub-command help")
        # See https://stackoverflow.com/questions/8757338/
        subparsers._parser_class = argparse.ArgumentParser

        # Poster slideshow.
        slideshow = subparsers.add_parser("slideshow",
            help="run the poster slideshow",
            formatter_class=self._FORMATTER_CLASS)
        self.add_default_arguments(slideshow)
        self.add_geometry(slideshow)
        self.add_pause(slideshow)
        self.add_advance(slideshow)
        self.add_fading(slideshow)
        self.add_datetime(slideshow)
        self.add_logging_level(slideshow)
        slideshow.set_defaults(runner=self.start_slideshow)

        # Program browser.
        browser = subparsers.add_parser("browse",
            help="run the program browser",
            formatter_class=self._FORMATTER_CLASS)
        self.add_default_arguments(browser)
        self.add_geometry(browser)
        self.add_pause(browser)
        self.add_advance(browser)
        self.add_logging_level(browser)
        browser.set_defaults(runner=self.start_browser)

        # Program directory.
        directory = subparsers.add_parser("directory",
            help="run the session directory",
            formatter_class=self._FORMATTER_CLASS)
        self.add_default_arguments(directory)
        self.add_geometry(directory)
        self.add_advance(directory)
        self.add_datetime(directory)
        self.add_logging_level(directory)
        directory.set_defaults(runner=self.start_directory)

        # Dump a text report on the program.
        report = subparsers.add_parser("report",
            help="dump a text report on the program",
            formatter_class=self._FORMATTER_CLASS)
        self.add_config_file(report)
        self.add_logging_level(report)
        report.set_defaults(runner=self.dump_report)

    def add_config_file(self, parser: argparse.ArgumentParser) -> None:
        """Add an option for the input file.
        """
        parser.add_argument('cfgfile', type=str,
            help='path to the input excel configuration file')

    def add_default_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add the default arguments to the given parser.
        """
        self.add_config_file(parser)
        parser.add_argument('--conference-name', type=str, default='16th Pisa Meeting on Advanced Detectors',
            help='the conference name')
        parser.add_argument('--conference-dates', type=str, default='La Biodola, Isola d\'Elba',
            help='the conference dates')
        parser.add_argument('--conference-location', type=str, default='May 26-June 1, 2024',
            help='the conference location')

    def add_geometry(self, parser: argparse.ArgumentParser, default_header_height: int=310):
        """Add all the geometry options.
        """
        parser.add_argument('--mode', type=str, default='fullscreen', choices=VALID_DISPLAY_MODES,
            help='display geometry')
        parser.add_argument('--poster-width', type=int, default=None,
            help='width of the poster display (taken from the screen size by default)')
        parser.add_argument('--header-height', type=int, default=default_header_height,
            help='height of the poster header')
        parser.add_argument('--portrait-height', type=int, default=132,
            help='height of the presenter portraits and QR codes')

    @staticmethod
    def add_datetime(parser: argparse.ArgumentParser) -> None:
        """Add an option to fake a different running date.
        """
        parser.add_argument('--display-date', type=str, default=None,
            help='optional date, e.g., 23/05/2022')
        parser.add_argument('--display-time', type=str, default='12:00',
            help='optional time, e.g., 12:00')

    @staticmethod
    def add_pause(parser: argparse.ArgumentParser, default: float=300.) -> None:
        """Add the pause interval option.
        """
        parser.add_argument('--pause-interval', type=float, default=default,
             help='pause time interval [s]')

    @staticmethod
    def add_advance(parser: argparse.ArgumentParser, default: float=30.) -> None:
        """Add the advance interval option.
        """
        parser.add_argument('--advance-interval', type=float, default=default,
             help='pause time interval [s]')

    @staticmethod
    def add_fading(parser: argparse.ArgumentParser) -> None:
        """Add the fading effect option.
        """
        parser.add_argument('--fading', action='store_true',
            help='enable the fading effect between posters')
        parser.add_argument('--no-fading', action='store_false',
            help='disable the fading effect between posters')
        parser.set_defaults(fading=False)

    @staticmethod
    def add_logging_level(parser: argparse.ArgumentParser) -> None:
        """Add an option for the input file.
        """
        parser.add_argument("--logging_level", type=str, choices=logging_.logging_levels(),
                            default="INFO",
                            help="logging level")

    def start_slideshow(self, **kwargs) -> None:
        """Start the poster slideshow.
        """
        app = QApplication(sys.argv)
        # Determine the appropriate poster width from the screen size unless this is
        # explicitly overridden via command-line options.
        if kwargs.get('poster_width') is None:
            poster_width = app.screens()[0].size().width() - 20
            logger.info('Setting posted width to %d (based on the screen size)', poster_width)
            kwargs['poster_width'] = poster_width
        window = SlideShow(**kwargs)
        sys.exit(app.exec_())

    def start_browser(self, **kwargs) -> None:
        """Start the program browser.
        """
        app = QApplication(sys.argv)
        # Determine the appropriate poster width from the screen size unless this is
        # explicitly overridden via command-line options.
        if kwargs.get('poster_width') is None:
            poster_width = app.screens()[0].size().width() - 20
            logger.info('Setting posted width to %d (based on the screen size)', poster_width)
            kwargs['poster_width'] = poster_width
        window = ProgramBrowser(**kwargs)
        sys.exit(app.exec_())

    def start_directory(self, **kwargs) -> None:
        """Start the session directory.
        """
        app = QApplication(sys.argv)
        # Determine the appropriate poster width from the screen size unless this is
        # explicitly overridden via command-line options.
        if kwargs.get('poster_width') is None:
            poster_width = app.screens()[0].size().width() - 20
            logger.info('Setting posted width to %d (based on the screen size)', poster_width)
            kwargs['poster_width'] = poster_width
        window = SessionDirectory(**kwargs)
        sys.exit(app.exec_())

    def dump_report(self, **kwargs) -> None:
        """Dump a text report on the program.
        """
        program = PosterProgram(kwargs.get('cfgfile'))
        program.dump_report()

    def run(self) -> None:
        """Run the actual command tied to the specific options.
        """
        kwargs = vars(self.parse_args())
        # Setup logging.
        logging_.setup_logger(kwargs.pop("logging_level"))
        # Call the appropriate runner function.
        runner = kwargs.pop("runner")
        return runner(**kwargs)



def main() -> None:
    """Main entry point.
    """
    start_message()
    CliArgumentParser().run()


if __name__ == "__main__":
    main()
