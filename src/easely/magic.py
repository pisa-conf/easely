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

"""Magic lock file mechanism.

This is a simple lock-file mechanism that was introduced for debugging purposes, in
order to be able to trigger a reload of the program by simply creating a .reload
file in the top-level easely folder.
"""

import pathlib

from loguru import logger

_MAGIC_FOLDER_PATH = pathlib.Path(__file__).parent.parent.parent
_MAGIC_FILE_PATH = _MAGIC_FOLDER_PATH / ".reload"


def read_magic_file() -> bool:
    """Read the magic file and remove it if it exists.

    Returns:
        bool: True if the magic file was found and removed, False otherwise.
    """
    if _MAGIC_FILE_PATH.exists():
        logger.info("Magic file found!")
        _MAGIC_FILE_PATH.unlink()
        logger.info("Magic file removed.")
        return True
    return False
