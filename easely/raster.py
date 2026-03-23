# Copyright (C) 2024, luca.baldini@pi.infn.it
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

"""Rasterization tools.
"""

import os
import subprocess
import sys

import cv2
from loguru import logger
import numpy as np
import pdfrw
import PIL
import PIL.Image

from pisameet import PISAMEET_DATA


# Move upstream
DEFAULT_LOGURU_HANDLER = dict(sink=sys.stderr, colorize=True, format=">>> <level>{message}</level>")
logger.remove()
logger.add(**DEFAULT_LOGURU_HANDLER)

REFERENCE_DENSITY = 72.
EXIF_ORIENTATION_TAG = 274
EXIF_ROTATION_DICT = {3: 180, 6: 270, 8: 90}
HAARCASCADE_FILE_PATH = os.path.join(PISAMEET_DATA, 'haarcascade_frontalface_default.xml')


def pdf_page_size(file_path: str, page_number: int=0) -> tuple[int, int]:
    """Return the page size for a given page of a given pdf document.

    Arguments
    ---------
    file_path : str
        The path to the input pdf file.

    page_number : int
        The target page number (starting from zero).
    """
    if not file_path.endswith('.pdf'):
        raise RuntimeError(f'{file_path} not a pdf file?')
    logger.debug(f'Retrieving page {page_number} size from {file_path}...')
    document = pdfrw.PdfReader(file_path)
    page = document.pages[page_number]
    # This is a list of strings, e.g., ['0', '0', '1683.72', '2383.92']...
    bbox = page.MediaBox or page.Parent.MediaBox
    # ... which we convert to a list of float, e.g., [0, 0, 1683.72, 2383.92]
    bbox = [float(val) for val in bbox]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    logger.debug(f'Page size: ({width}, {height}).')
    return width, height


def pdf_to_png(input_file_path: str, output_file_path: str, density: float = REFERENCE_DENSITY,
    compression_level: int = 0) -> str:
    """Convert a .pdf file to a .png file using imagemagick convert under the hood.

    See https://imagemagick.org/script/command-line-options.php for some basic
    information about convert's internals.

    Arguments
    ---------
    input_file_path : str
        The path to the input pdf file.

    output_file_path : str
        The path to the output rasterized file.

    density : int
        The density (in dpi) to be passed to convert.
    """
    if not input_file_path.endswith('.pdf'):
        raise RuntimeError(f'{input_file_path} not a pdf file?')
    logger.info(f'Converting {input_file_path} to {output_file_path} @{density:.3f} dpi...')
    subprocess.run(['convert', '-density', f'{density}', '-define',
        f'png:compression-level={compression_level}', input_file_path, output_file_path],
        check=True)
    return output_file_path


def resize_image(img, width, height, output_file_path=None, resample=PIL.Image.LANCZOS,
    reducing_gap=3., compression_level=6):
    """Base function to resize an image.
    """
    w, h = img.size
    logger.info(f'Resizing image ({w}, {h}) -> ({width}, {height})...')
    img = img.resize((width, height), resample, None, reducing_gap)
    if output_file_path is not None:
        logger.info(f'Saving image to {output_file_path}...')
        img.save(output_file_path, compress_level=compression_level)


def png_resize_to_width(input_file_path: str, output_file_path: str, width: int, **kwargs):
    """Resize an image to the target width.
    """
    with PIL.Image.open(input_file_path) as img:
        w, h = img.size
        height = round(width / w * h)
        resize_image(img, width, height, output_file_path, **kwargs)


def png_resize_to_height(input_file_path: str, output_file_path: str, height: int, **kwargs):
    """Resize an image to the target height.
    """
    with PIL.Image.open(input_file_path) as img:
        w, h = img.size
        width = round(height / h * w)
        resize_image(img, width, height, output_file_path, **kwargs)


def png_horizontal_autocrop(input_file_path: str, output_file_path: str,
    threshold: float = 0.99, padding: float = 0.001, compression_level=6, max_aspect_ratio=1.52):
    """
    """
    logger.info(f'Cropping image {input_file_path}...')
    with PIL.Image.open(input_file_path) as img:
        logger.debug('Decoding image data...')
        width, height = img.size
        channel = lambda ch: np.array(img.getdata(0)).reshape((height, width))
        data = sum(channel(ch) for ch in (0, 1, 2))
        threshold *= data.max()
        padding = int(padding * width + 1)
        hist = data.mean(axis=0)
        edges, = np.where(np.diff(hist > threshold))
        xmin = max(edges.min() - padding, 0)
        xmax = min(edges.max() + padding + 1, width)
        deltax = (xmax - xmin)
        if height / deltax > max_aspect_ratio:
            logger.warning(f'Cropped width ({deltax}) exceeds maximum aspect ratio')
            pad = int(0.5 * (height / max_aspect_ratio - deltax))
            logger.debug(f'Padding back by {pad} pixels...')
            xmin -= pad
            xmax += pad
        ratio = deltax / width
        logger.debug(f'Horizontal compression ratio: {ratio:.3f}')
        bbox = (xmin, 0, xmax, height)
        logger.debug(f'Target bounding box: {bbox}')
        img = img.crop(bbox)
        logger.info(f'Saving cropped image to {output_file_path}')
        img.save(output_file_path, compress_level=compression_level)


def png_horizontal_padding(input_file_path: str, output_file_path: str, aspect_ratio=1.50):
    """
    """
    logger.info(f'Padding image {input_file_path}...')
    with PIL.Image.open(input_file_path) as img:
        width, height = img.size
        target_width = int(height / aspect_ratio)
        delta = target_width - width
        logger.debug(f'Padding to {target_width} x {height}...')
        output = PIL.Image.new(img.mode, (target_width, height), (255, 255, 255))
        output.paste(img, (delta // 2, 0))
        output.save(output_file_path)


def raster_pdf(input_file_path: str, output_file_path: str, target_width: int,
    intermediate_width: int = None, overwrite: bool = False, autocrop: bool = False,
    max_aspect_ratio=1.52) -> str:
    """Raster a pdf file and convert it to a png.
    """
    if os.path.exists(output_file_path) and not overwrite:
        logger.info(f'Output file {output_file_path} exists, skipping...')
        return
    logger.info(f'Rastering {input_file_path}...')
    original_width, original_height = pdf_page_size(input_file_path)
    aspect_ratio = original_height / original_width
    # Are we skipping the intermediate rastering?
    if intermediate_width is None or intermediate_width <= target_width:
        logger.debug('Skipping intermediate rastering...')
        density = target_width / original_width * REFERENCE_DENSITY
        return pdf_to_png(input_file_path, output_file_path, density)
    logger.debug('Performing intermediate rastering...')
    density = intermediate_width / original_width * REFERENCE_DENSITY
    file_path = pdf_to_png(input_file_path, output_file_path, density)
    if autocrop:
        png_horizontal_autocrop(file_path, file_path)
    elif aspect_ratio > max_aspect_ratio:
        logger.warning(f'Aspect ratio ({aspect_ratio:.3f}) is too large for {input_file_path}!')
        png_horizontal_padding(file_path, file_path)
    logger.debug('Resizing to target width...')
    return png_resize_to_width(file_path, file_path, target_width)


def face_bbox(file_path: str, min_frac_size: float = 0.145, padding: float = 1.85):
    """Run a simple opencv face detection and return the proper bounding box for
    cropping the input image.

    This is returning an approximately square (modulo 1 pixel possible difference
    between the two sides) bounding box containing the face.
    """
    logger.info(f'Running face detection on {file_path}...')
    # Run opencv and find the face.
    cascade = cv2.CascadeClassifier(HAARCASCADE_FILE_PATH)
    img = cv2.imread(file_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = img.shape
    min_size = round(width * min_frac_size), round(height * min_frac_size)
    faces = cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=min_size)
    if len(faces) == 0:
        logger.warning('No candidate face found, returning dummy bounding box...')
        x0, y0 = width // 2, height // 2
        half_side = round(0.5 * min(width, height))
        return (x0 - half_side, y0 - half_side, x0 + half_side, y0 + half_side)
    logger.debug(f'{len(faces)} candidate bounding boxes found...')
    if len(faces) > 1:
        for i, face in enumerate(faces):
            logger.debug(f'{i}: {face}')
    # Here we have to be clever on whether we want the first, the last or one particular
    # bounding box, in case more than one are found.
    x, y, w, h = faces[0]
    # Calculate the starting center and size.
    x0, y0 = x + w // 2, y + h // 2
    half_side = round(0.5 * max(w, h) * padding)
    # First pass on the bounding box.
    xmin = max(x0 - half_side, 0)
    ymin = max(y0 - half_side, 0)
    xmax = min(x0 + half_side, width - 1)
    ymax = min(y0 + half_side, height - 1)
    # Second pass to avoid exceeding the physical dimensions of the original image.
    w = xmax - xmin
    h = ymax - ymin
    if h > w:
        delta = (h - w) // 2
        ymin += delta
        ymax -= delta
    elif h < w:
        delta = (w - h) // 2
        xmin += delta
        xmax -= delta
    w = xmax - xmin
    h = ymax - ymin
    if abs(w - h) > 1:
        logger.warning(f'Skewed bounding box ({w} x {h})')
    bbox = (xmin, ymin, xmax, ymax)
    logger.info(f'{len(faces)} face candidate(s) found, returning {bbox}...')
    return bbox


def crop_to_face(file_path: str, output_file_path: str, height: int,
    overwrite: bool = False, bbox=None, **kwargs):
    """Resize a given input file to contain the face.
    """
    if os.path.exists(output_file_path) and not overwrite:
        logger.info(f'Output file {output_file_path} exists, skipping...')
        return
    logger.info(f'Cropping {file_path} to face...')
    kwargs.setdefault('resample', PIL.Image.ANTIALIAS)
    kwargs.setdefault('reducing_gap', 3.)
    try:
        with PIL.Image.open(file_path) as img:
            # Parse the original image size and orientation.
            w, h = img.size
            orientation = img.getexif().get(EXIF_ORIENTATION_TAG, None)
            logger.debug(f'Original size: {w} x {h}, orientation: {orientation}')
            # If the image is rotated, we need to change the orientation.
            if orientation in EXIF_ROTATION_DICT:
                rotation = EXIF_ROTATION_DICT[orientation]
                logger.debug(f'Applying a rotation by {rotation} degrees...')
                img = img.rotate(rotation, expand=True)
                w, h = img.size
                logger.debug(f'Rotated size: {w} x {h}')
            # Crop and scale to the target dimensions.
            if bbox is None:
                bbox = face_bbox(file_path)
            logger.info(f'Resizing image to ({height}, {height})...')
            img = img.resize((height, height), box=bbox, **kwargs)
            if output_file_path is not None:
                logger.info(f'Saving image to {output_file_path}...')
                img.save(output_file_path)
    except PIL.UnidentifiedImageError as exception:
        logger.error(exception)
