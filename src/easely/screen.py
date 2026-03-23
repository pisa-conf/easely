# Copyright (C) 2021--2026 the easely team.
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

"""Screen ID management.

In a conference setup each raspberry pi will be connected to a single screen, and will
be responsible for showing the content on that screen, which is dictated by the
underlying program file.

The package comes with a sample configuration file containing a single integer in text
form, which is automatically copied to the proper location if the actual screen
configuration file does not exist, and which the user can then edit by hand to set the
screen identifier for each raspberry pi. Note the screen configuration file is included
in the .gitignore file, so it will not be tracked by git.
"""

import pathlib
import shutil

from loguru import logger

_SCREEN_ID_FOLDER_PATH = pathlib.Path(__file__).parent
_SCREEN_ID_FILE_PATH = _SCREEN_ID_FOLDER_PATH / "screen.cfg"
_SAMPLE_SCREEN_ID_FILE_PATH = _SCREEN_ID_FOLDER_PATH / "screen.cfg.sample"


def read_screen_id():
    """Read the screen identifier from the local configuration file.

    Note that if the proper text files does not exists, a copy from a sample file will be
    created, for the user to edit it by hand.
    """
    if not _SCREEN_ID_FILE_PATH.exists():
        logger.info("Screen configuration file not found, copying the default one.")
        shutil.copyfile(_SAMPLE_SCREEN_ID_FILE_PATH, _SCREEN_ID_FILE_PATH)
    logger.info(f"Reading the screen identifier from {_SCREEN_ID_FILE_PATH}...")
    with open(_SCREEN_ID_FILE_PATH) as input_file:
        screen_id = int(input_file.read())
    logger.info(f"Local screen identifier: {screen_id}")
    return screen_id