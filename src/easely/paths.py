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
from typing import List

from .logging_ import logger
from .typing_ import PathLike


PROGRAM_FILE_NAME = "program"


class WorkspaceLayout(str, Enum):

    """Small Enum class with the basic folder structure within each conference root folder.
    """

    ATTACHMENTS = "indico_attachments"
    QRCODES = "qrcodes"
    POSTERS = "posters"
    HEADSHOTS = "presenters"
    RASTERED_POSTERS = "posters_raster"
    CROPPED_HEADSHOTS = "presenters_crop"


def contribution_file_name(friendly_id: int, suffix: str) -> str:
    """Return the standardized file name for a contribution file, given its
    ``friendly_id`` on indico and the expected suffix.

    Arguments
    ---------
    friendly_id : int
        The contribution friendly id on indico

    suffix : str
        The target file suffix, including the dot, e.g., ".pdf" or ".jpg

    Returns
    -------
    str
        The standardized file name for the contribution file, e.g., "0001.pdf".
    """
    return f"{friendly_id:04d}{suffix}"


def friendly_id(file_path: pathlib.Path) -> int:
    """Return the friendly id corresponding to a given contribution file path, by
    parsing the file name.

    Return None if the file name does not start with an integer friendly id.

    Arguments
    ---------
    file_path : pathlib.Path
        The path to the contribution file, from which we want to extract the friendly id.

    Returns
    -------
    int or None
        The friendly id corresponding to the given contribution file path,
        or None if the file name does not start with an integer friendly id.
    """
    prefix = file_path.stem.split("_")[0]
    try:
        return int(prefix)
    except ValueError:
        return None


def filter_dir(input_dir: pathlib.Path, friendly_ids: List[int] = None) -> List[pathlib.Path]:
    """Filter the list of files in a given input directory, by keeping only those whose
    contribution id is in the given list of friendly ids.

    Note that, while when we know the file type this can be done programmatically,
    in the general case you really need to filter the list from the complete one.

    Arguments
    ---------
    input_dir : pathlib.Path
        The path to the input directory, from which we want to filter the files.

    friendly_ids : list of int, optional
        The list of contribution friendly ids to keep (None to keep all files).

    Returns
    -------
    list of pathlib.Path
        The list of file paths in the input directory.
    """
    file_list = sorted(file_path for file_path in input_dir.iterdir() if file_path.is_file())
    if friendly_ids is None:
        return file_list
    filtered_file_list = []
    for file_path in file_list:
        _id = friendly_id(file_path)
        if _id is None:
            logger.warning(f"Skipping file with unexpected name format: {file_path}")
            continue
        elif _id in friendly_ids:
            filtered_file_list.append(file_path)
    return filtered_file_list


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