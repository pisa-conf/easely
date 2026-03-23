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

"""Dispatching facilities.

This module contains the facilities to dispatch all the relevant files from the
dump of the indico attachments to the folder structure in use by the slideshow.
"""

import os
import shutil

import pdfrw

from . import logger


def pdf_info(file_path: str):
    """Peek at a pdf file and retrieve some of its basic properties, e.g., the
    number of pages and the aspect ratio, useful to decide whether it is a poster or not.

    Arguments
    ---------
    file_path : str
        Path to the input pdf file.
    """
    # pylint: disable=broad-except
    assert file_path.endswith('.pdf')
    try:
        pdf = pdfrw.PdfReader(file_path)
    except Exception as exception:
        logger.error('Parsing error for %s: %s', file_path, exception)
        return None, None
    num_pages = len(pdf.pages)
    box = pdf.pages[0].MediaBox or pdf.pages[0].Parent.MediaBox
    if box is None:
        logger.warning('No media box for %s...', file_path)
        return num_pages, None
    if float(box[3]) == 0:
        logger.warning(f'zero height for {file_path}')
        return num_pages, None
    aspect_ratio = float(box[2]) / float(box[3])
    return num_pages, aspect_ratio


def poster_candidates(file_list):
    """Filter an input list of file paths and return the subset of those that
    might legitimately point to actual posters.
    """
    candidates = []
    for file_path in file_list:
        if file_path.endswith('.pdf'):
            num_pages, aspect_ratio = pdf_info(file_path)
            if num_pages == 1 and aspect_ratio is not None and aspect_ratio < 1:
                candidates.append(file_path)
    return candidates


def dispatch_posters(contribution_ids, src_folder_path, dest_folder_path):
    """Dispatch the candidate poster files from the indico attachment folder to
    the target folder holding the poster originals.
    """
    file_dict = {id_: [] for id_ in contribution_ids}
    for file_name in os.listdir(src_folder_path):
        if not file_name.endswith('.pdf'):
            continue
        id_ = int(file_name.split('-')[0])
        if id_ in file_dict:
            file_dict[id_].append(os.path.join(src_folder_path, file_name))
    for id_, attachments in file_dict.items():
        if len(attachments) == 0:
            logger.error('No poster candidate found for contribution %d', id_)
            continue
        candidates = poster_candidates(attachments)
        if len(candidates) == 1:
            logger.info('Unique poster candidate found!')
            src = candidates[0]
            file_name = f'{id_:03d}.pdf'
            dest = os.path.join(dest_folder_path, file_name)
            if os.path.exists(dest):
                logger.info('Target file %s exist, skipping...', dest)
            else:
                logger.info('Copying over poster to %s...', dest)
                shutil.copyfile(src, dest)
        else:
            logger.warning('%d candidate posters / %d attachments for contribution %s',
                len(candidates), len(attachments), id_)


def dispatch_pictures(contribution_ids, src_folder_path, dest_folder_path):
    """
    """
    logger.info('Dispatching pictures...')
    file_dict = {id_: [] for id_ in contribution_ids}
    for file_name in os.listdir(src_folder_path):
        if not file_name.split('.')[-1].lower() in ('png', 'jpg', 'jpeg'):
            continue
        id_ = int(file_name.split('-')[0])
        if id_ in file_dict:
            file_dict[id_].append(os.path.join(src_folder_path, file_name))
    for id_, attachments in file_dict.items():
        if len(attachments) == 0:
            logger.error('No picture candidate found for contribution %d', id_)
            continue
        if len(attachments) == 1:
            logger.info('Unique picture candidate found!')
            src = attachments[0]
            ext = attachments[0].split('.')[-1]
            file_name = f'{id_:03d}.{ext}'
            dest = os.path.join(dest_folder_path, file_name)
            if os.path.exists(dest):
                logger.info('Target file %s exist, skipping...', dest)
            else:
                logger.info('Copying over poster to %s...', dest)
                shutil.copyfile(src, dest)
        else:
            logger.warning('%d candidate pictures found for contribution %d...',
                len(attachments), id_)
    logger.info('Done.')
