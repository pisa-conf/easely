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

from loguru import logger
import numpy as np
import PIL
import PIL.Image


EXIF_ORIENTATION_TAG = 274
EXIF_ROTATION_DICT = {3: 180, 6: 270, 8: 90}



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
