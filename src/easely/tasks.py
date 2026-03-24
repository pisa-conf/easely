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

"""Task definition for the command-line interface.
"""

import pathlib
from dataclasses import dataclass

from . import pdf
from . import img
from . import __name__ as __package_name__
from .logging_ import logger
from .typing_ import PathLike

# Default output directory for generated files.
DEFAULT_OUTPUT_DIR = pathlib.Path.home() / f"{__package_name__}data"
DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)


def sanitize_path(path: PathLike, suffix: str = None, check_exists: bool = True) -> pathlib.Path:
    """Sanitize the input file path, i.e, convert it to a pathlib.Path object,
    ensuring it exists and has the correct suffix.

    Arguments
    ---------
    path : PathLike
        The input file path (either a string or a pathlib.Path object).

    suffix : str, optional
        The expected file suffix (None to disengage the check).

    check_exists : bool
        Whether to check if the file exists (default True).

    Returns
    -------
    pathlib.Path
        The sanitized file path, as a pathlib.Path object.
    """
    path = pathlib.Path(path)
    if check_exists and not path.exists():
        raise RuntimeError(f"{path} does not exist")
    if suffix is not None and path.suffix != suffix:
        raise RuntimeError(f"{path} is not a {suffix} file")
    return path


@dataclass(frozen=True)
class RasterDefaults:
    """Default values for rasterization parameters.
    """
    output_folder: PathLike = DEFAULT_OUTPUT_DIR
    output_file_name: str = None
    target_width: int = 2120
    intermediate_width: int = 4240
    max_aspect_ratio: float = 1.52
    overwrite: bool = False
    autocrop: bool = True


def raster(
        input_file_path: PathLike,
        output_folder: PathLike = RasterDefaults.output_folder,
        output_file_name: str = RasterDefaults.output_file_name,
        target_width: int = RasterDefaults.target_width,
        intermediate_width: int = RasterDefaults.intermediate_width,
        max_aspect_ratio: float = RasterDefaults.max_aspect_ratio,
        overwrite: bool = RasterDefaults.overwrite,
        autocrop: bool = RasterDefaults.autocrop,
        ) -> pathlib.Path:
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

    output_folder : PathLike
        The path to the output folder.

    output_file_name : str, optional
        The name of the output file.

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
    input_file_path = sanitize_path(input_file_path, ".pdf")
    output_folder = sanitize_path(output_folder)
    if output_file_name is None:
        output_file_name = input_file_path.stem + ".png"
    output_file_path = output_folder / output_file_name
    logger.info(f"Rasterizing {input_file_path} with target width {target_width}...")
    if output_file_path.exists() and not overwrite:
        logger.info(f"Output file {output_file_path} exists, skipping...")
        return output_file_path
    # Run imagemagick to convert the pdf to png---note this is slightly different
    # depending on whether we want to perform an intermediate rasterization step or not.
    if intermediate_width is None or intermediate_width <= target_width:
        return pdf.run_imagemagick(input_file_path, output_file_path, target_width)
    file_path = pdf.run_imagemagick(input_file_path, output_file_path, intermediate_width)

    # Need some significant refactoring, here. We should open the image file once,
    # and then operate on the PIL.Image object in memory, instead of saving intermediate
    # results to disk and reopening them. More or less all the facilities should be
    # in the raster2.py module. Once we do that, we will not need to recalculate the
    # page size.
    original_width, original_height = pdf.page_size(input_file_path)
    aspect_ratio = original_height / original_width
    if autocrop:
        img.png_horizontal_autocrop(file_path, file_path)
    elif aspect_ratio > max_aspect_ratio:
        logger.warning(f'Aspect ratio ({aspect_ratio:.3f}) is too large for {input_file_path}!')
        img.png_horizontal_padding(file_path, file_path)
    logger.debug('Resizing to target width...')
    return img.png_resize_to_width(file_path, file_path, target_width)