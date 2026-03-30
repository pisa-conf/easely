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
from enum import Enum

from easely import __name__ as __package_name__
from easely import __version__, logging_
from easely.__qt__ import bootstrap_window
from easely.gui import PosterProgram, ProgramBrowser, SessionDirectory, SlideShow
from easely import tasks


def start_message() -> None:
    """Print the start message.
    """
    msg = f"""
    This is {__package_name__} version {__version__}.

    Copyright (C) 2022--2026, the {__package_name__} team.

    {__package_name__} comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it under certain
    conditions. See the LICENSE file for details.

    Visit https://github.com/pisa-conf/{__package_name__} for more information.
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

    DEFAULT = "default"
    MAXIMIZE = "maximize"
    FULLSCREEN = "fullscreen"


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

        # Download the indico attachments for the poster sessions.
        download = subparsers.add_parser("download",
            help="download the program information from indico",
            formatter_class=self._FORMATTER_CLASS)
        download.add_argument("url", type=str,
            help="the indico url for the conference")
        download.add_argument("--output-folder", type=str,
            default=tasks.DownloadDefaults.output_folder,
            help="the output folder for the generated files")
        download.add_argument("--file-types", nargs="+", type=str,
            default=tasks.DownloadDefaults.file_types,
            help="the file types to be downloaded")
        download.add_argument("--overwrite", action="store_true",
            help="overwrite existing output files")
        self.add_logging_level(download)
        download.set_defaults(runner=tasks.download)

        # Generate the excel roster.
        roster = subparsers.add_parser("roster",
            help="dump the poster roster to an excel file",
            formatter_class=self._FORMATTER_CLASS)
        roster.add_argument("--file-path", type=str,
            default=tasks.RosterDefaults.file_path,
            help="the input .json file with the event data")
        roster.add_argument("--overwrite", action="store_true",
            help="overwrite existing output files")
        self.add_logging_level(roster)
        roster.set_defaults(runner=tasks.roster)

        # Generate QR codes for the poster attachments.
        qrcodes = subparsers.add_parser("qrcodes",
            help="generate QR codes for the poster attachments",
            formatter_class=self._FORMATTER_CLASS)
        qrcodes.add_argument("--file-path", type=str,
            default=tasks.QrcodesDefaults.file_path,
            help="the input .json file with the event data")
        qrcodes.add_argument("--overwrite", action="store_true",
            help="overwrite existing output files")
        self.add_logging_level(qrcodes)
        qrcodes.set_defaults(runner=tasks.qrcodes)

        # Rasterize one or more posters.
        rasterize = subparsers.add_parser("rasterize",
            help="rasterize one or more posters",
            formatter_class=self._FORMATTER_CLASS)
        rasterize.add_argument("input_files", nargs="+", type=str,
            help="path to the input pdf file(s)")
        rasterize.add_argument("--output-folder", type=str,
            default=tasks.RasterizeDefaults.output_folder,
            help="the output folder for the generated png file(s)")
        rasterize.add_argument("--target-width", type=int,
            default=tasks.RasterizeDefaults.target_width,
            help="the target width for the generated png file(s)")
        rasterize.add_argument("--intermediate-width", type=int,
            default=tasks.RasterizeDefaults.intermediate_width,
            help="the intermediate width for the generated png file(s)")
        rasterize.add_argument("--autocrop", action="store_true",
            help="perform an horizontal autocrop after the initial rasterization step")
        rasterize.add_argument("--max-aspect-ratio", type=float,
            default=tasks.RasterizeDefaults.max_aspect_ratio,
            help="the maximum aspect ratio for the generated png file(s)")
        rasterize.add_argument("--overwrite", action="store_true",
            help="overwrite existing output files")
        self.add_logging_level(rasterize)
        rasterize.set_defaults(runner=self.rasterize)

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

    @staticmethod
    def add_config_file(parser: argparse.ArgumentParser) -> None:
        """Add an option for the input configuration file.
        """
        parser.add_argument("cfgfile", type=str,
            help="path to the input excel configuration file")

    def add_default_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add the default arguments to the given parser.
        """
        self.add_config_file(parser)
        parser.add_argument("--conference-name", type=str,
            default="16th Pisa Meeting on Advanced Detectors",
            help="the conference name")
        parser.add_argument("--conference-dates", type=str,
            default="La Biodola, Isola d'Elba",
            help="the conference dates")
        parser.add_argument("--conference-location", type=str,
            default="May 26-June 1, 2024",
            help="the conference location")

    @staticmethod
    def add_geometry(parser: argparse.ArgumentParser, default_header_height: int=310):
        """Add all the geometry options.
        """
        parser.add_argument("--mode", type=str, default="fullscreen", choices=VALID_DISPLAY_MODES,
            help="display geometry")
        parser.add_argument("--poster-width", type=int, default=None,
            help="width of the poster display (from the screen size by default)")
        parser.add_argument("--header-height", type=int, default=default_header_height,
            help="height of the poster header")
        parser.add_argument("--portrait-height", type=int, default=132,
            help="height of the presenter portraits and QR codes")

    @staticmethod
    def add_datetime(parser: argparse.ArgumentParser) -> None:
        """Add an option to fake a different running date.
        """
        parser.add_argument("--display-date", type=str, default=None,
            help="optional date, e.g., 23/05/2022")
        parser.add_argument("--display-time", type=str, default="12:00",
            help="optional time, e.g., 12:00")

    @staticmethod
    def add_pause(parser: argparse.ArgumentParser, default: float=300.) -> None:
        """Add the pause interval option.
        """
        parser.add_argument("--pause-interval", type=float, default=default,
             help="pause time interval [s]")

    @staticmethod
    def add_advance(parser: argparse.ArgumentParser, default: float=30.) -> None:
        """Add the advance interval option.
        """
        parser.add_argument("--advance-interval", type=float, default=default,
             help="pause time interval [s]")

    @staticmethod
    def add_fading(parser: argparse.ArgumentParser) -> None:
        """Add the fading effect option.
        """
        parser.add_argument("--fading", action="store_true",
            help="enable the fading effect between posters")
        parser.add_argument("--no-fading", action="store_false",
            help="disable the fading effect between posters")
        parser.set_defaults(fading=False)

    @staticmethod
    def add_logging_level(parser: argparse.ArgumentParser) -> None:
        """Add an option for the input file.
        """
        parser.add_argument("--logging_level", type=str, choices=logging_.logging_levels(),
                            default="INFO",
                            help="logging level")

    def download(self, **kwargs) -> None:
        """Download the program information and associated attachments from indico.
        """
        tasks.download(**kwargs)

    def rasterize(self, **kwargs) -> None:
        """Rasterize one or more posters.
        """
        for file_path in kwargs.pop("input_files"):
            tasks.rasterize(file_path, **kwargs)

    def start_slideshow(self, **kwargs) -> None:
        """Start the poster slideshow.
        """
        return bootstrap_window(SlideShow, **kwargs)

    def start_browser(self, **kwargs) -> None:
        """Start the program browser.
        """
        return bootstrap_window(ProgramBrowser, **kwargs)

    def start_directory(self, **kwargs) -> None:
        """Start the session directory.
        """
        return bootstrap_window(SessionDirectory, **kwargs)

    def dump_report(self, **kwargs) -> None:
        """Dump a text report on the program.
        """
        program = PosterProgram(kwargs.get("cfgfile"))
        program.dump_report()

    def run(self) -> None:
        """Run the actual command tied to the specific options.
        """
        kwargs = vars(self.parse_args())
        logging_.setup_logger(kwargs.pop("logging_level"))
        runner = kwargs.pop("runner")
        return runner(**kwargs)


def main() -> None:
    """Main entry point.
    """
    start_message()
    CliArgumentParser().run()


if __name__ == "__main__":
    main()
