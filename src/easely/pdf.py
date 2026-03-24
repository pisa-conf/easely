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

from . import raster
from .logging_ import logger
from .typing_ import PathLike


# Reference density for rasterization, in dpi, see
# https://imagemagick.org/script/command-line-options.php
_DEFAULT_RESOLUTION = 72.


def _sanitize_file_path(file_path: PathLike, suffix: str, check_exists: bool = True) -> pathlib.Path:
    """Sanitize the input file path, i.e, convert it to a pathlib.Path object,
    ensuring it exists and has the correct suffix.

    Arguments
    ---------
    file_path : PathLike
        The input file path (either a string or a pathlib.Path object).

    suffix : str
        The expected file suffix (None to disengage the check).

    check_exists : bool
        Whether to check if the file exists (default True).

    Returns
    -------
    pathlib.Path
        The sanitized file path, as a pathlib.Path object.
    """
    file_path = pathlib.Path(file_path)
    if check_exists and not file_path.is_file():
        raise RuntimeError(f"{file_path} does not exist or is not a file")
    if suffix is not None and file_path.suffix != suffix:
        raise RuntimeError(f"{file_path} is not a {suffix} file")
    return file_path


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
    file_path = _sanitize_file_path(file_path, ".pdf")
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


def _run_imagemagick(input_file_path: PathLike, output_file_path: PathLike,
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
    # Sanitize the input and output file paths.
    input_file_path = _sanitize_file_path(input_file_path, ".pdf")
    output_file_path = _sanitize_file_path(output_file_path, ".png", check_exists=False)
    # Calculate the density to be passed to convert, given the target width and the
    # original page size.
    page_width, _ = page_size(input_file_path)
    density = target_width / page_width * _DEFAULT_RESOLUTION
    # Run imagemagick convert to raster the pdf file and save it as a png file.
    logger.info(f"Converting {input_file_path} to {output_file_path} @{density:.3f} dpi...")
    subprocess.run(["magick", "-density", f"{density}", "-define",
        f"png:compression-level={compression_level}", input_file_path, output_file_path],
        check=True)
    return output_file_path


def raster_pdf(input_file_path: PathLike, output_file_path: PathLike, target_width: int,
               intermediate_width: int = None, overwrite: bool = False,
               autocrop: bool = False, max_aspect_ratio=1.52) -> pathlib.Path:
    """Raster a pdf file and convert it to a png.

    This is the main function to convert a poster pdf file to a png file. Since
    posters are typically shown on a screen with a portrait orientation, all the
    process is driven by the target width of the final image---ideally we want an
    a rastered image with the same number of pixels as the physical QPixmap object
    on the screen, so that we don't have to perform any resizing at runtime.

    In order to maximize the quality of the final image, we offer the possibility
    to perform an intermediate rasterization step at a higher resolution, followed
    by a resizing to the target width where we can take advantage of the high-quality
    resampling algorithms available in PIL. An intermediate rasterization at twice
    the target width, e.g., is typically very effective.

    Additionally, the function provides an option to automatically crop the rastered
    image to its content (horizontally), which allows for maximizing the screen use.

    Arguments
    ---------
    input_file_path : PathLike
        The path to the input pdf file.

    output_file_path : PathLike
        The path to the output rasterized (png) file.

    target_width : int
        The target width for the output png file.

    intermediate_width : int, optional
        The intermediate width to be used for the initial rasterization step. If None
        or smaller than target_width, the intermediate rasterization step is skipped.

    overwrite : bool, optional
        Whether to overwrite the output file if it already exists (default False).

    autocrop : bool, optional
        Whether to perform an horizontal autocrop after the initial rasterization
        step (default False).

    max_aspect_ratio : float, optional
        The maximum aspect ratio (height / width) allowed for the final image.

    Returns
    -------
    pathlib.Path
        The path to the output rasterized (png) file.
    """
    # Sanitize the input and output file paths, and check if the output file already exists.
    input_file_path = _sanitize_file_path(input_file_path, ".pdf")
    output_file_path = _sanitize_file_path(output_file_path, ".png", check_exists=False)
    logger.info(f"Rasterizing {input_file_path} with target width {target_width}...")
    if output_file_path.exists() and not overwrite:
        logger.info(f"Output file {output_file_path} exists, skipping...")
        return output_file_path
    # Run imagemagick to convert the pdf to png---note this is slightly different
    # depending on whether we want to perform an intermediate rasterization step or not.
    if intermediate_width is None or intermediate_width <= target_width:
        return _run_imagemagick(input_file_path, output_file_path, target_width)
    file_path = _run_imagemagick(input_file_path, output_file_path, intermediate_width)

    # Need some significant refactoring, here. We should open the image file once,
    # and then operate on the PIL.Image object in memory, instead of saving intermediate
    # results to disk and reopening them. More or less all the facilities should be
    # in the raster2.py module. Once we do that, we will not need to recalculate the
    # page size.
    original_width, original_height = page_size(input_file_path)
    aspect_ratio = original_height / original_width
    if autocrop:
        raster.png_horizontal_autocrop(file_path, file_path)
    elif aspect_ratio > max_aspect_ratio:
        logger.warning(f'Aspect ratio ({aspect_ratio:.3f}) is too large for {input_file_path}!')
        raster.png_horizontal_padding(file_path, file_path)
    logger.debug('Resizing to target width...')
    return raster.png_resize_to_width(file_path, file_path, target_width)