# Copyright (C) 2024--2026, the easely team.
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

"""pdf manipulation facilities.
"""

import pathlib
import subprocess
from typing import Tuple

import pdfrw

from .logging_ import logger
from .typing_ import PathLike


# Reference density for rasterization, in dpi, see
# https://imagemagick.org/script/command-line-options.php
_DEFAULT_RESOLUTION = 72.


def page_size(file_path: PathLike, page_number: int = 0) -> Tuple[float, float]:
    """Return the page size for a given page of a given pdf document.

    Arguments
    ---------
    file_path : PathLike
        The path to the input pdf file.

    page_number : int
        The target page number (starting from zero).

    Returns
    -------
    Tuple[float, float]
        The page size, as a tuple of (width, height).
    """
    logger.debug(f"Retrieving page {page_number} size from {file_path}...")
    document = pdfrw.PdfReader(file_path)
    page = document.pages[page_number]
    # This is a list of strings, e.g., ['0', '0', '1683.72', '2383.92']...
    bbox = page.MediaBox or page.Parent.MediaBox
    # ... which we convert to a list of float, e.g., [0, 0, 1683.72, 2383.92]
    bbox = [float(val) for val in bbox]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    logger.debug(f"Page size: ({width}, {height}).")
    return width, height


def run_imagemagick(input_file_path: PathLike, output_file_path: PathLike,
                    target_width: int, compression_level: int = 0) -> pathlib.Path:
    """Convert a .pdf file to a .png file using imagemagick convert under the hood.

    Note the `convert` command is deprecated in IMv7 in favor of `magick` or
    `magick convert`.

    See https://imagemagick.org/script/command-line-options.php for some basic
    information about convert's internals.

    Arguments
    ---------
    input_file_path : PathLike
        The path to the input pdf file.

    output_file_path : PathLike
        The path to the output rasterized (png) file.

    target_width : int
        The target width for the output png file in pixels.

    compression_level : int, optional
        The PNG compression level to be passed to convert.
        Levels range from 0 (no compression, fastest) to 9 (maximum compression, slowest).
        Note the compression only affects size, not image quality.
    """
    # Calculate the density to be passed to convert.
    page_width, _ = page_size(input_file_path)
    density = target_width / page_width * _DEFAULT_RESOLUTION
    # Run imagemagick convert to raster the pdf file and save it as a png file.
    logger.info(f"Converting {input_file_path} to {output_file_path} @{density:.3f} dpi...")
    subprocess.run(["magick", "-density", f"{density}", "-define",
        f"png:compression-level={compression_level}", input_file_path, output_file_path],
        check=True)
    return output_file_path
