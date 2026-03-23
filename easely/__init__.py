#
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


"""Program-wise facilities.
"""


import logging
import os
import shutil
import sys

#
# System-wide environment settings.
#
PACKAGE_NAME = 'pisameet'
PISAMEET_ROOT = os.path.abspath(os.path.dirname(__file__))
PISAMEET_BASE = os.path.abspath(os.path.join(PISAMEET_ROOT, os.pardir))
PISAMEET_DATA = os.path.join(PISAMEET_BASE, 'data')
PISAMEET_GRAPHICS = os.path.join(PISAMEET_BASE, 'graphics')

MISSING_PICTURE_PATH = os.path.join(PISAMEET_GRAPHICS, 'unknown_female.png')
MISSING_POSTER_PATH = os.path.join(PISAMEET_GRAPHICS, 'pisameet2024.png')
MISSING_QRCODE_PATH = os.path.join(PISAMEET_GRAPHICS, 'unknown_qrcode.png')

# Magic file to induce a reload in the apps that support it.
MAGIC_FILE_PATH = os.path.join(PISAMEET_BASE, '.reload')


class TerminalColors:

    """Terminal facilities for printing text in colors.
    """

    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def _color(text, color):
        """Process a piece of tect to be printed out in color.
        """
        return '%s%s%s' % (color, text, TerminalColors.ENDC)

    @staticmethod
    def red(text):
        """Process a piece of text to be printed out in red.
        """
        return TerminalColors._color(text, TerminalColors.RED)

    @staticmethod
    def yellow(text):
        """Process a piece of text to be printed out in yellow.
        """
        return TerminalColors._color(text, TerminalColors.YELLOW)

    @staticmethod
    def green(text):
        """Process a piece of text to be printed out in green.
        """
        return TerminalColors._color(text, TerminalColors.GREEN)


def abort(msg=''):
    """Abort the execution of the program.
    """
    sys.exit(TerminalColors.red(f'Abort: {msg}'))



class TerminalFormatter(logging.Formatter):

    """Logging terminal formatter class.
    """

    def format(self, record):
        """Overloaded format method.
        """
        text = ('>>> %s' % record.msg)
        if len(record.args) > 0:
            text = text % record.args
        if record.levelno >= logging.ERROR:
            text = TerminalColors.red(text)
        elif record.levelno == logging.WARNING:
            text = TerminalColors.yellow(text)
        return text


#Configure the main terminal logger.
logger = logging.getLogger('pisameet')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(TerminalFormatter())
logger.addHandler(console_handler)


# Relevant files for setting up the screen ID.
_SCREEN_ID_FILE_PATH = os.path.join(PISAMEET_ROOT, 'screen.cfg')
_SAMPLE_SCREEN_ID_FILE_PATH = os.path.join(PISAMEET_ROOT, 'screen.cfg.sample')


def copy_screen_id_sample_file():
    """Copy the sample configuration file with the screen identifier to the
    proper location, for it to be manually edited.
    """
    src = _SAMPLE_SCREEN_ID_FILE_PATH
    dest = _SCREEN_ID_FILE_PATH
    logger.info('Copying %s to %s...', src, dest)
    shutil.copyfile(src, dest)


def read_screen_id():
    """Read the screen identifier from the local configuration file.

    Note that if the proper text files does not exists, a copy from a sample
    file will be created, for the user to edit it by hand.
    (The configuration file is included in the .gitignore file.)
    """
    if not os.path.exists(_SCREEN_ID_FILE_PATH):
        copy_screen_id_sample_file()
    logger.info('Reading tyeh screen identifier from %s...', _SCREEN_ID_FILE_PATH)
    with open(_SCREEN_ID_FILE_PATH) as input_file:
        screen_id = int(input_file.read())
    logger.info('Local screen identifier: %d', screen_id)
    return screen_id


def read_magic_file():
    """
    """
    if os.path.exists(MAGIC_FILE_PATH):
        logger.info('Magic file found!')
        os.remove(MAGIC_FILE_PATH)
        logger.info('Magic file removed.')
        return 1
    return 0
