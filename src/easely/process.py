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

"""Pre-processing tools.
"""

import os



def crawl(folder_path: str, file_type: str = '.pdf', filter_pattern: str = None) -> list:
    """Crawl a given folder recursively and return a list of all the files of
    a given type matching a given pattern.

    Arguments
    ---------
    folder_path : str
        The path to the root folder to be recursively crawled.

    file_type : str
        The file extension, including the dot (e.g., '.pdf')

    filter_pattern : str
        An optional filtering pattern---if not None, only the files containing
        the pattern in the name are retained.

    Return
    ------
    A list of absolute file paths.
    """
    file_list = []
    for root, _, files in os.walk(folder_path):
        file_list += [os.path.join(root, file) for file in files if file.endswith(file_type)]
    file_list.sort()
    if filter_pattern is not None:
        file_list = [file_path for file_path in file_list \
            if filter_pattern in os.path.basename(file_path)]
    return file_list
