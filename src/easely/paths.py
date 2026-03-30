# Copyright (C) 2026, the easely team.
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

"""General utilities for managing file paths.
"""

import pathlib
from enum import Enum

from .logging_ import logger
from .typing_ import PathLike


PROGRAM_FILE_NAME = "program"


class WorkspaceLayout(str, Enum):

    """Small Enum class with the basic folder structure within each conference root folder.
    """

    ATTACHMENTS = "attachments"
    QRCODES = "qrcodes"
    POSTERS = "posters"
    SLIDES = "slides"
    HEADSHOTS = "headshots"
    RASTERED_POSTERS = "rastered_posters"
    CROPPED_HEADSHOTS = "cropped_headshots"


def sanitize_file_path(path: PathLike, suffix: str = None, check_exists: bool = False) -> pathlib.Path:
    """Sanitize a file path, i.e, convert it to a pathlib.Path object, optionally
    ensuring it comes with the correct suffix and/or exists.

    Note this can be used for both input and output file paths, depending on the values of the
    suffix and check_exists parameters.

    Arguments
    ---------
    path : PathLike
        The file path (either a string or a pathlib.Path object).

    suffix : str, optional
        The expected file suffix (None to disengage the check).

    check_exists : bool
        Whether to check if the file exists.

    Returns
    -------
    pathlib.Path
        The sanitized file path, as a pathlib.Path object.
    """
    path = pathlib.Path(path)
    if check_exists and not path.is_file():
        raise RuntimeError(f"{path} does not exist or is not a file")
    if suffix is not None and path.suffix != suffix:
        raise RuntimeError(f"{path} is not a {suffix} file")
    return path


def sanitize_folder_path(path: PathLike, create: bool = False) -> pathlib.Path:
    """Sanitize a folder path, i.e, convert it to a pathlib.Path object and, optionally,
    create it if it does not exist.

    Arguments
    ---------
    path : PathLike
        The path to the output folder.

    create : bool
        Whether to create the folder if it does not exist.

    Returns
    -------
    pathlib.Path
        The path to the output folder, as a pathlib.Path object.
    """
    path = pathlib.Path(path)
    if not path.exists() and create:
        logger.info(f"Creating folder {path}...")
        path.mkdir(parents=True)
    return path