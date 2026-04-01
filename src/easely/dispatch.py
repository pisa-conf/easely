# Copyright (C) 2022--2026, the easely team.
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

"""Dispatching facilities.

This module contains the facilities to dispatch all the relevant files from the
dump of the indico attachments to the folder structure in use by the slideshow.
"""

import os
import pathlib
import shutil
from typing import Dict, List

from .logging_ import logger
from .paths import sanitize_folder_path
from .typing_ import PathLike


def populate_file_dict(friendly_ids: List[int], input_dir: PathLike,
                       file_types: List[str]) -> Dict[int, List[pathlib.Path]]:
    """
    Populate a dictionary mapping friendly IDs to lists of file paths in a given directory.

    Arguments
    ---------
    friendly_ids : List[int]
        The list of friendly IDs for which to populate file paths.

    input_dir : PathLike
        The path to the directory containing the files.

    file_types : List[str]
        The list of file extensions to consider.

    Returns
    -------
    Dict[int, List[pathlib.Path]]
        A dictionary mapping each friendly ID to a list of matching file paths.
    """
    file_dict = {id_: [] for id_ in friendly_ids}
    for file_path in sorted(input_dir.iterdir()):
        if not file_path.suffix.lower() in file_types:
            continue
        # Note this does not depend on how much zeros we use for padding the file names.
        id_ = int(file_path.stem.split("-")[0])
        if id_ in file_dict:
            file_dict[id_].append(file_path)
    return file_dict


def dispatch_file(src: pathlib.Path, dest: pathlib.Path) -> bool:
    """
    Copy a file from the source to the destination path.

    Arguments
    ---------
    src : pathlib.Path
        The path to the source file.

    dest : pathlib.Path
        The path to the destination file.

    Returns
    -------
    bool
        True if the file was copied, False if the destination file already exists.
    """
    if dest.is_file():
        logger.debug(f"Target file {dest} exist, skipping...")
        return False
    logger.debug(f"Copying over {src} -> {dest}...")
    shutil.copyfile(src, dest)
    return True


def dispatch_posters(friendly_ids: List[int], attachments_dir: PathLike,
    posters_dir: PathLike, pattern: str = "poster") -> int:
    """Dispatch the candidate poster files from the indico attachment folder to
    the target folder holding the poster originals.

    Arguments
    ---------
    attachments_dir : PathLike
        The path to the folder containing the indico attachments.

    posters_dir : PathLike
        The path to the folder where the poster files should be copied to.

    pattern : str
        The pattern to look for in the file names to identify the poster files.

    Returns
    -------
    int
        The number of files successfully copied.
    """
    logger.info("Dispatching posters...")
    attachments_dir = sanitize_folder_path(attachments_dir)
    posters_dir = sanitize_folder_path(posters_dir, create=True)
    num_dispatched = 0
    # Do a first pass for the .pdf files matching the list of friendly ids for the posters.
    file_dict = populate_file_dict(friendly_ids, attachments_dir, [".pdf"])
    # Do a second pass and find best candidates for the actual poster files.
    for id_, file_list in file_dict.items():
        # If there is no file in the list, we have nothing to dispatch...
        if len(file_list) == 0:
            logger.error(f"No .pdf attachment found for contribution {id_}")
            continue
        dest = posters_dir / f"{id_:04d}.pdf"
        # Match the list of pdf files with the expected pattern.
        matches = [file_path for file_path in file_list if pattern in file_path.name.lower()]
        if len(matches) == 1:
            # There is a unique strict match, and we are golden!
            if dispatch_file(matches[0], dest):
                num_dispatched += 1
        elif len(matches) == 0:
            # No strict match, but if there is a single .pdf attachment, and chance are
            # that the presented did not stick to the naming conventions.
            if len(file_list) == 1:
                logger.warning(f"Unique .pdf attachment for contribution {id_}, but not a match.")
                if dispatch_file(file_list[0], dest):
                    num_dispatched += 1
            # Too many pdf files---somebody should look into this and resolve the ambiguity.
            else:
                logger.error(f"{len(file_list)} .pdf attachments for contribution {id_} without any match, skipping...")
        elif len(matches) > 1:
            # Most likely the presenter did upload multiple versions of the poster, and we
            # and we would be better off deleting the old one from indico.
            logger.error(f"Multiple matches found for contribution {id_}, skipping...")
    logger.info(f"Done, {num_dispatched} file(s) physically copied.")
    return num_dispatched


def dispatch_headshots(friendly_ids: List[int], attachments_dir: PathLike,
    headshots_dir: PathLike, pattern: str = "picture") -> int:
    """Dispatch the candidate headshot files from the indico attachment folder to
    the target folder holding the headshot originals.

    Arguments
    ---------
    attachments_dir : PathLike
        The path to the folder containing the indico attachments.

    headshots_dir : PathLike
        The path to the folder where the headshot files should be copied to.

    pattern : str
        The pattern to look for in the file names to identify the headshot files.

    Returns
    -------
    int
        The number of files successfully copied.
    """
    logger.info("Dispatching headshots...")
    attachments_dir = sanitize_folder_path(attachments_dir)
    headshots_dir = sanitize_folder_path(headshots_dir, create=True)
    num_dispatched = 0
    # Do a first pass for the graphics files matching the list of friendly ids for the posters.
    file_dict = populate_file_dict(friendly_ids, attachments_dir, [".png", ".jpg", ".jpeg"])
    # Do a second pass and find best candidates for the actual poster files.
    for id_, file_list in file_dict.items():
    # If there is no file in the list, we have nothing to dispatch...
        if len(file_list) == 0:
            logger.error(f"No graphics attachment found for contribution {id_}")
            continue
        # Match the list of graphics files with the expected pattern.
        matches = [file_path for file_path in file_list if pattern in file_path.name.lower()]
        if len(matches) == 1:
            # There is a unique strict match, and we are golden!
            dest = headshots_dir / f"{id_:04d}{matches[0].suffix}"
            if dispatch_file(matches[0], dest):
                num_dispatched += 1
        elif len(matches) == 0:
            # No strict match, but if there is a single graphics attachment, and chance are
            # that the presented did not stick to the naming conventions.
            if len(file_list) == 1:
                logger.warning(f"Unique graphics attachment for contribution {id_}, but not a match.")
                dest = headshots_dir / f"{id_:04d}{file_list[0].suffix}"
                if dispatch_file(file_list[0], dest):
                    num_dispatched += 1
            # Too many graphics files---somebody should look into this and resolve the ambiguity.
            else:
                logger.error(f"{len(file_list)} graphics attachments for contribution {id_} without any match, skipping...")
        elif len(matches) > 1:
            # Most likely the presenter did upload multiple versions of the poster, and we
            # and we would be better off deleting the old one from indico.
            logger.error(f"Multiple matches found for contribution {id_}, skipping...")
    logger.info(f"Done, {num_dispatched} file(s) physically copied.")
    return num_dispatched
