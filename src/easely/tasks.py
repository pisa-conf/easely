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
from typing import Tuple

from . import pdf
from . import img
from . import indico2 as indico
from . import __name__ as __package_name__
from .logging_ import logger
from .paths import WorkspaceLayout, sanitize_file_path, sanitize_folder_path, PROGRAM_FILE_NAME
from .typing_ import PathLike


@dataclass(frozen=True)
class DownloadDefaults:

    """Default values for the download task parameters.
    """

    output_folder: PathLike = pathlib.Path.cwd()
    file_types: Tuple[str] = ("pdf", "ppt", "pptx", "png", "jpg", "jpeg")
    overwrite: bool = False


def download(
        url: str,
        output_folder: PathLike = DownloadDefaults.output_folder,
        file_types: Tuple[str] = DownloadDefaults.file_types,
        overwrite: bool = DownloadDefaults.overwrite
        ) -> None:
    """Download all the poster attachments for a given indico event.

    Note that the .json file with the event data will be downloaded in the
    output folder passed as an argument, and is always overwritten. The actual
    poster attachments will be downloaded in a subfolder.

    Arguments
    ---------
    url : str
        The indico url for the conference, e.g., https://agenda.infn.it/export/event/37033.json

    output_folder : PathLike
        The output folder for the generated files.

    file_types : Tuple[str]
        The file types to be downloaded, e.g., ("pdf", "ppt", "pptx", "png", "jpg", "jpeg").

    overwrite : bool
        Whether to overwrite the output files if they already exist (default False).
    """
    output_folder = sanitize_folder_path(output_folder, create=True)
    file_path = output_folder / f"{PROGRAM_FILE_NAME}.json"
    indico.download_event_data(url, file_path, overwrite=True)
    attachments_folder = output_folder / WorkspaceLayout.ATTACHMENTS
    kwargs = dict(file_types=file_types, overwrite=overwrite)
    indico.Event(file_path).download_poster_attachments(attachments_folder, **kwargs)


@dataclass(frozen=True)
class RosterDefaults:

    """Default values for roster task parameters.
    """

    file_path: PathLike = pathlib.Path.cwd() / f"{PROGRAM_FILE_NAME}.json"
    overwrite: bool = False


def roster(
        file_path: PathLike = RosterDefaults.file_path,
        overwrite: bool = RosterDefaults.overwrite
        ) -> PathLike:
    """Generate a roster of poster presenters.

    Arguments
    ---------
    file_path : PathLike
        The path to the .json file with the event data.

    overwrite : bool
        Whether to overwrite the output file if it already exists (default False).
    """
    file_path = sanitize_file_path(file_path, suffix=".json", check_exists=True)
    output_file_path = file_path.with_suffix(".xlsx")
    indico.Event(file_path).generate_poster_roster(output_file_path, overwrite=overwrite)
    return output_file_path


@dataclass(frozen=True)
class DispatchDefaults:

    """Default values for dispatch task parameters.
    """

    pass


def dispatch() -> None:
    """Dispatch.
    """
    pass


@dataclass(frozen=True)
class RasterizeDefaults:

    """Default values for rasterization task parameters.
    """

    output_folder: PathLike = pathlib.Path.cwd() / WorkspaceLayout.RASTERED_POSTERS
    output_file_name: str = None
    target_width: int = 2120
    intermediate_width: int = 4240
    max_aspect_ratio: float = 1.52
    overwrite: bool = False
    autocrop: bool = True


def rasterize(
        input_file_path: PathLike,
        output_folder: PathLike = RasterizeDefaults.output_folder,
        output_file_name: str = RasterizeDefaults.output_file_name,
        target_width: int = RasterizeDefaults.target_width,
        intermediate_width: int = RasterizeDefaults.intermediate_width,
        autocrop: bool = RasterizeDefaults.autocrop,
        max_aspect_ratio: float = RasterizeDefaults.max_aspect_ratio,
        overwrite: bool = RasterizeDefaults.overwrite
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

    autocrop : bool, optional
        Whether to perform an horizontal autocrop after the initial rasterization
        step (default False).

    max_aspect_ratio : float, optional
        The maximum aspect ratio (height / width) allowed for the final image.

    overwrite : bool, optional
        Whether to overwrite the output file if it already exists (default False).

    Returns
    -------
    pathlib.Path
        The path to the output rasterized (png) file.
    """
    input_file_path = sanitize_file_path(input_file_path, suffix=".pdf", check_exists=True)
    output_folder = sanitize_folder_path(output_folder, create=True)
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


@dataclass(frozen=True)
class FacecropDefaults:

    """Default values for face cropping task parameters.
    """

    pass


def facecrop() -> None:
    """Face crop.
    """
    pass