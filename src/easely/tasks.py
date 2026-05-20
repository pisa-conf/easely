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
from typing import List, Tuple

from . import pdf
from . import face
from . import img
from . import indico
from . import __name__ as __package_name__
from .dispatch import dispatch_headshots, dispatch_posters
from .logging_ import logger
from .paths import WorkspaceLayout, conference_poster_path, filter_dir, sanitize_file_path, \
    sanitize_folder_path, ASSETS_DIR, DEFAULT_FILE_NAME, PROGRAM_FILE_NAME
from .program import Program
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
    attachments_folder = output_folder / WorkspaceLayout.ATTACHMENTS.value
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
class QrcodesDefaults:

    """Default values for QR code generation task parameters.
    """

    file_path: PathLike = pathlib.Path.cwd() / f"{PROGRAM_FILE_NAME}.json"
    folder_path: PathLike = pathlib.Path.cwd() / WorkspaceLayout.QRCODES.value
    size: int = 250
    overwrite: bool = False


def qrcodes(
        file_path: PathLike = QrcodesDefaults.file_path,
        folder_path: PathLike = QrcodesDefaults.folder_path,
        size: int = QrcodesDefaults.size,
        overwrite: bool = QrcodesDefaults.overwrite
        ) -> None:
    """Generate QR codes for the poster attachments.

    Arguments
    ---------
    file_path : PathLike
        The path to the .json file with the event data.

    folder_path : PathLike
        The path to the output folder for the QR codes.

    size : int
        The size of the generated QR codes, in pixels.

    overwrite : bool
        Whether to overwrite the output files if they already exist (default False).
    """
    file_path = sanitize_file_path(file_path, suffix=".json", check_exists=True)
    output_folder = sanitize_folder_path(folder_path, create=True)
    indico.Event(file_path).generate_qrcodes(output_folder, size=size, overwrite=overwrite)


@dataclass(frozen=True)
class DispatchDefaults:

    """Default values for dispatch task parameters.
    """

    file_path: PathLike = pathlib.Path.cwd() / f"{PROGRAM_FILE_NAME}.json"
    attachments_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.ATTACHMENTS.value
    posters_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.POSTERS.value
    headshots_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.HEADSHOTS.value


def dispatch(
        attachments_dir: PathLike = DispatchDefaults.attachments_dir,
        posters_dir: PathLike = DispatchDefaults.posters_dir,
        headshots_dir: PathLike = DispatchDefaults.headshots_dir
        ) -> None:
    """Dispatch the files from the attachments folder to the appropriate destination folders.
    """
    ids = indico.Event(DispatchDefaults.file_path).poster_contributions_ids()
    dispatch_posters(ids, attachments_dir, posters_dir)
    dispatch_headshots(ids, attachments_dir, headshots_dir)


@dataclass(frozen=True)
class RasterizeDefaults:

    """Default values for rasterization task parameters.
    """

    input_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.POSTERS.value
    targets: List[int] = None
    output_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.RASTERED_POSTERS.value
    tool: pdf.Raster = pdf.Raster.PYMUPDF
    target_width: int = 2120
    intermediate_width: int = 4240
    autocrop: bool = True
    autocrop_threshold: int = 0
    max_aspect_ratio: float = 1.52
    overwrite: bool = False


def rasterize(
        input_dir: PathLike = RasterizeDefaults.input_dir,
        targets: List[int] = RasterizeDefaults.targets,
        output_dir: PathLike = RasterizeDefaults.output_dir,
        tool: pdf.Raster = RasterizeDefaults.tool,
        target_width: int = RasterizeDefaults.target_width,
        intermediate_width: int = RasterizeDefaults.intermediate_width,
        autocrop: bool = RasterizeDefaults.autocrop,
        autocrop_threshold: int = RasterizeDefaults.autocrop_threshold,
        max_aspect_ratio: float = RasterizeDefaults.max_aspect_ratio,
        overwrite: bool = RasterizeDefaults.overwrite
        ) -> int:
    """Raster a pdf file and convert it to a png.

    This is the main function to convert a poster pdf file to a png file. Since
    posters are typically shown on a screen with a portrait orientation, all the
    process is driven by the target width of the final image---ideally we want an
    a rasterized image with the same number of pixels as the physical QPixmap object
    on the screen, so that we don't have to perform any resizing at runtime.

    In order to maximize the quality of the final image, we offer the possibility
    to perform an intermediate rasterization step at a higher resolution, followed
    by a resizing to the target width where we can take advantage of the high-quality
    resampling algorithms available in PIL. An intermediate rasterization at twice
    the target width, e.g., is typically very effective.

    Additionally, the function provides an option to automatically crop the rasterized
    image to its content (horizontally), which allows for maximizing the screen use.

    Arguments
    ---------
    input_dir : PathLike
        The path to the input folder containing the pdf files to be rasterized.

    output_dir : PathLike
        The path to the output folder.

    target_width : int
        The target width for the output png file.

    intermediate_width : int, optional
        The intermediate width to be used for the initial rasterization step. If None
        or smaller than target_width, the intermediate rasterization step is skipped.

    autocrop : bool, optional
        Whether to perform an horizontal autocrop after the initial rasterization
        step (default False).

    autocrop_threshold : int, optional (default 0)
        The threshold to be used for the autocrop step, in the range [0, 255].

    max_aspect_ratio : float, optional
        The maximum aspect ratio (height / width) allowed for the final image.

    overwrite : bool, optional
        Whether to overwrite the output file if it already exists (default False).

    Returns
    -------
    int
        The number of files successfully rasterized.
    """
    input_dir = sanitize_folder_path(input_dir)
    output_dir = sanitize_folder_path(output_dir, create=True)
    # Populate the input file list
    file_list = filter_dir(input_dir, targets)
    # Add the actual conference poster.
    poster_path = conference_poster_path(input_dir.parent)
    if poster_path.is_file() and targets is None:
        file_list.append(poster_path)
    # Ready to go.
    num_rasterized = 0
    logger.info(f"Rasterizing poster files...")
    for input_file_path in file_list:
        if input_file_path.suffix.lower() != ".pdf":
            raise RuntimeError(f"{input_file_path} is not a pdf file")
        output_file_path = output_dir / input_file_path.with_suffix(".png").name
        if output_file_path.exists() and not overwrite:
            logger.debug(f"Output file {output_file_path} exists, skipping...")
            continue
        logger.info(f"Rasterizing {input_file_path} with target width {target_width}...")
        if output_file_path.exists() and not overwrite:
            logger.info(f"Output file {output_file_path} exists, skipping...")
            return output_file_path

        # Run imagemagick to convert the pdf to png---note this is slightly different
        # depending on whether we want to perform an intermediate rasterization step or not.
        if intermediate_width is None or intermediate_width <= target_width:
            return pdf.pdf_to_png(tool, input_file_path, output_file_path, target_width)
        file_path = pdf.pdf_to_png(tool, input_file_path, output_file_path, intermediate_width)

        # And, finally, work on the rasterized image.
        image = img.open_image(file_path)
        if autocrop:
            image = img.autocrop_image(image, autocrop_threshold)
        image = img.resize_image(image, target_width)
        aspect_ratio = image.height / image.width
        # Check the aspect ratio.
        if aspect_ratio > max_aspect_ratio:
            logger.warning(f"Aspect ratio {aspect_ratio:.2f} too large, padding...")
            # Calculate the necessary horizontal padding on both sides to match the
            # desired aspect ratio, and pad the image accordingly.
            delta = int(0.5 * (image.height / max_aspect_ratio - image.width))
            image = img.pad_image(image, (delta, 0, delta, 0))
        image.save(file_path)
        num_rasterized += 1
    logger.info(f"Done, {num_rasterized} poster files rasterized.")
    return num_rasterized


@dataclass(frozen=True)
class FacecropDefaults:

    """Default values for face cropping task parameters.
    """

    input_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.HEADSHOTS.value
    targets: List[int] = None
    output_dir: PathLike = pathlib.Path.cwd() / WorkspaceLayout.CROPPED_HEADSHOTS.value
    size: int = QrcodesDefaults.size
    circular_mask: bool = False
    model: face.FaceDetection = face.FaceDetection.CASCADE
    detect_kwargs: dict = None
    min_fractional_area: float = 0.02
    horizontal_padding: float = 0.5
    top_scale_factor: float = 1.25
    interactive: bool = False
    overwrite: bool = False


def facecrop(
        input_dir: PathLike = FacecropDefaults.input_dir,
        targets: List[int] = FacecropDefaults.targets,
        output_dir: PathLike = FacecropDefaults.output_dir,
        size: int = FacecropDefaults.size,
        circular_mask: bool = FacecropDefaults.circular_mask,
        model: face.FaceDetection = FacecropDefaults.model,
        detect_kwargs: dict = FacecropDefaults.detect_kwargs,
        min_fractional_area: float = FacecropDefaults.min_fractional_area,
        horizontal_padding: float = FacecropDefaults.horizontal_padding,
        top_scale_factor: float = FacecropDefaults.top_scale_factor,
        interactive: bool = FacecropDefaults.interactive,
        overwrite: bool = FacecropDefaults.overwrite
        ) -> int:
    """Crop the headshots provided by the poster presenters to square images centered
    on the actual faces.

    Arguments
    ---------
    input_dir : PathLike
        The path to the input folder containing the original headshot images.

    output_dir : PathLike
        The path to the output folder for the cropped headshot images.

    size : int
        The size of the output cropped headshot images, in pixels.

    circular_mask : bool
        Whether to apply a circular mask to the output cropped headshot images.

    model : face.FaceDetection
        The face-detection model to use.

    detect_kwargs : dict
        Additional optional keyword arguments to be passed to the face-detection model.

    min_fractional_area : float
        The minimum area of the detected face bounding box as a fraction of the original
        image area. Objects smaller than that are ignored.

    horizontal_padding : float
        The horizontal padding to be added to the detected face bounding box, as a fraction
        of the bounding box width.

    top_scale_factor : float
        The scale factor to be applied to the top side of the detected face bounding box.

    interactive : bool
        Whether to display the detected face bounding box and the final enlarged bounding box
        on the original image, for debugging purposes.

    overwrite : bool
        Whether to overwrite the output files if they already exist (default False).

    Returns
    -------
    int
        The number of files successfully cropped.
    """
    input_dir = sanitize_folder_path(input_dir)
    output_dir = sanitize_folder_path(output_dir, create=True)
    # Place the (resized) default headshot image to the output folder, unless
    # we are specifying one or more target contributions.
    if targets is None:
        dest = output_dir / f"{DEFAULT_FILE_NAME}.png"
        if not dest.exists() or overwrite:
            logger.info(f"Resizing default headshot image...")
            src = ASSETS_DIR / "headshot_generic.jpg"
            image = img.open_image(src)
            image = img.resize_image(image, width=size)
            img.save_image(image, dest)
    num_cropped = 0
    # Cache all the arguments and keyword arguments for the function call inside the loop.
    if detect_kwargs is None:
        detect_kwargs = {}
    args = size, circular_mask, model, min_fractional_area, detect_kwargs, \
        horizontal_padding, top_scale_factor, interactive, overwrite
    file_list = filter_dir(input_dir, targets)
    logger.info(f"Cropping faces for {len(file_list)} target files...")
    for input_file_path in file_list:
        output_file_path = output_dir / input_file_path.with_suffix(".png").name
        if face.crop_face(input_file_path, output_file_path, *args) is not None:
            num_cropped += 1
    logger.info(f"Done, {num_cropped} face images cropped.")
    return num_cropped


@dataclass(frozen=True)
class ReportDefaults:

    """Default values for report generation task parameters.
    """

    file_path: PathLike = pathlib.Path.cwd() / f"{PROGRAM_FILE_NAME}.xlsx"


def report(file_path: PathLike = ReportDefaults.file_path) -> None:
    """Generate a report of the program configuration.

    Arguments
    ---------
    file_path : PathLike
        The path to the program excel file.
    """
    program = Program(file_path)
    program.dump_report()