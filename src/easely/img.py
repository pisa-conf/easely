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

"""Rasterization tools.
"""

import os
import pathlib

import cv2
from loguru import logger
import numpy as np
import PIL
import PIL.Image

_OPENCV_DATA_FOLDER_PATH = pathlib.Path(__file__).parent.parent.parent / "data"

EXIF_ORIENTATION_TAG = 274
EXIF_ROTATION_DICT = {3: 180, 6: 270, 8: 90}
HAARCASCADE_FILE_PATH = _OPENCV_DATA_FOLDER_PATH / 'haarcascade_frontalface_default.xml'



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
