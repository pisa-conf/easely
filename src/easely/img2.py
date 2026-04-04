# Copyright (C) 2024--2026 the easely team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""Various facilities to operate on raster images.
"""

from __future__ import annotations

import dataclasses
import numbers
import random
from typing import Tuple

from loguru import logger
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageOps

from .typing_ import PathLike


@dataclasses.dataclass
class Rectangle:

    """Small container class representing a rectangle.

    Following the opencv conventions, a rectangle is identified by the two coordinates
    of the top-left corner, its with, and its height. The x coordinate is running
    from left to right, and the y coordinate is running from top to bottom, with
    the (0, 0) pixel placed at the top-left corner.

    Parameters
    ----------
    x0 : int
        The x coordinate of the upper-left corner of the rectangle.

    y0 : int
        The y coordinate of the upper-left corner of the rectangle.

    width : int
        The width of the rectangle.

    height : int
        The height of the rectangle; if None, this is set to be equal to the width
        (i.e., by default the rectangle is a square).
    """

    # pylint: disable=invalid-name
    x0: int
    y0: int
    width: int
    height: int = None

    def __post_init__(self) -> None:
        """Post initialization code.
        """
        # By deafult, generate a square.
        if self.height is None:
            self.height = self.width
        # Also, make sure all the members are integers, as we are dealing with
        # pixels in rasterized images. Note that we are using numbers.Integral, as
        # opposed to the native Python int, as we want to be able to catch the
        # numpy integral types as well.
        for item in (self.x0, self.y0, self.width, self.height):
            if not isinstance(item, numbers.Integral):
                raise RuntimeError(f'Wrong type for {self}')

    def copy(self) -> Rectangle:
        """Create an identical copy of the rectangle.

        Returns
        -------
        Rectangle
            A new Rectangle object, identical to the original one.
        """
        return Rectangle(self.x0, self.y0, self.width, self.height)

    @classmethod
    def square_from_size(cls, width: int, height: int) -> Rectangle:
        """Create a new object representing the largest square fitting within a
        given size, and centered within the corresponding area.

        Parameters
        ----------
        width : int
            The target width.

        height : int
            The target height.

        Returns
        -------
        Rectangle
            The largest centered, fitting square.
        """
        if width == height:
            return Rectangle(0, 0, width, height)
        side = min(width, height)
        delta = round(0.5 * (width - height))
        if delta > 0:
            return Rectangle(delta, 0, side, side)
        return Rectangle(0, -delta, side, side)

    def is_square(self) -> bool:
        """Return True if the rectangle is square.

        Returns
        -------
        bool
            True if the rectangle is squared.
        """
        return self.width == self.height

    def area(self) -> int:
        """Return the area of the rectangle.

        Returns
        -------
        int
            The area of the rectangle in pixel squared.
        """
        return self.width * self.height

    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Return the bounding box corresponding to the ractangle, in the form
        of the four-element tuple (xmin, ymin, xmax, ymax).

        Returns
        -------
        tuple[int, int, int, int]
            The four-element tuple corresponding to the rectangle bounding box.
        """
        return (self.x0, self.y0, self.x0 + self.width, self.y0 + self.width)

    @staticmethod
    def rounded_geometric_mean(*values: float, scale: float = None) -> int:
        """Return the geometric mean of the input parameters, rounded to the
        nearest integer.

        Parameters
        ----------
        values : float
            The values to be averaged.

        scale : float
            Optional multiplicative scale factor, to be applied before the geometric
            average is computed.

        Returns
        -------
        int
            The (rounded) geometric mean of the input data.
        """
        if scale is not None:
            values = [value * scale for value in values]
        return round(np.prod(values)**(1. / len(values)))

    def equivalent_square_side(self) -> int:
        """Return the side of the equivalent square, rounded to the nearest integer
        (which is basically the geometric mean of the rectangle width and height).

        Whenever the `fractional` word is used in the context of a rectangle, this
        is the scale constituting the multiplier for the operation at hand.

        Returns
        -------
        int
            The (rounded) side of the square with the same area as the rectangle.
        """
        return self.rounded_geometric_mean(self.width, self.height)

    def pad(self, top: int, right: int = None, bottom: int = None, left: int = None) -> Rectangle:
        """Create a new rectangle padding the original one according to the input
        parameters.

        Note that the order of the arguments is designed to make it easy for the
        user to specify a single padding on four sides (passing only one argument)
        different vertical and horizontal paddings (passing two arguments), as well
        as arbitrary configurations.

        Parameters
        ----------
        top : int
            The top padding in pixels.

        right : int
            The right padding in pixels.

        bottom : int
            The bottom padding in pixels.

        left : int
            The left padding in pixels.

        Returns
        -------
        Rectangle
            A new Rectangle object, properly padded with respect to the original one.
        """
        right = right or top
        bottom = bottom or top
        left = left or right
        rectangle = Rectangle(self.x0 - left, self.y0 - top, self.width + right + left,
            self.height + top + bottom)
        logger.debug(f'Padding {self} -> {rectangle}...')
        return rectangle

    def fits_within(self, width: int, height: int) -> bool:
        """Return whether the rectangle fits within a given area, possibly after
        a shift.

        Parameters
        ----------
        width : int
            The width of the target area.

        height : int
            The height of the target area.

        Returns
        -------
        bool
            True if the Rectangle fits.
        """
        return self.width <= width and self.height <= height

    def shift_to_fit(self, width: int, height: int) -> Rectangle:
        """Create a new Rectangle object by shifting the origin of the original
        one to make it fully contained in a given area, i.e. within the
        (0, 0, width, height) bounding box.

        Note this raises a RuntimeError if the rectangle is too large for the target
        area.

        Parameters
        ----------
        width : int
            The width of the target area.

        height : int
            The height of the target area.

        Returns
        -------
        Rectangle
            A new, shifted rectangle.
        """
        if not self.fits_within(width, height):
            raise RuntimeError(f'{self} does not fit into {width} x {height}')
        rectangle = self.copy()
        rectangle.x0 = int(np.clip(rectangle.x0, 0, width - rectangle.width))
        rectangle.y0 = int(np.clip(rectangle.y0, 0, height - rectangle.height))
        return rectangle

    def __eq__(self, other) -> bool:
        """Overloaded equality operator.
        """
        return self.x0 == other.x0 and self.y0 == other.y0 and \
            self.width == other.width and self.height == other.height

    def __lt__(self, other) -> bool:
        """Comparison operator---this is such that :class:`Ractangle` instances
        get sorted by area by default.
        """
        return self.area() < other.area()



def open_image(file_path: PathLike) -> PIL.Image.Image:
    """Open an existing image in read mode.

    Note the image is automatically rotated is the proper EXIF tag is found.

    Parameters
    ----------
    file_path
        The path to the image file.

    Returns
    -------
    PIL.Image.Image
        The actual image object.
    """
    logger.info(f'Loading image data from {file_path}...')
    with PIL.Image.open(file_path) as image:
        image = image.copy()
        PIL.ImageOps.exif_transpose(image, in_place=True)
    width, height = image.size
    logger.debug(f'Image size: {width} x {height}.')
    return image


def save_image(image: PIL.Image.Image, file_path: PathLike, **kwargs) -> None:
    """Save an image to file.

    This is a thin wrapper upon the PIL.Image.Image.save() function, where we
    don't allow the destination to be a file descriptor. All the keyword arguments
    that are supported for the various output format are thoroughly described at
    https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html

    Parameters
    ----------
    image : PIL.Image.Image
        The image to be saved.

    file_path : PathLike
        The path to the output file.

    kwargs
        The optional keyword arguments to be passed to the file writer.
    """
    logger.info(f'Saving image to {file_path} with parameters {kwargs}...')
    image.save(file_path, **kwargs)


def resize_image(image: PIL.Image.Image, width: int = None, height: int = None,
    resample=PIL.Image.Resampling.LANCZOS, box: Tuple[float, float, float, float] = None,
    reducing_gap: float = None) -> PIL.Image.Image:
    """Resize an existing image.

    This is basically calling PIL.Image.Image.resize() under the hood, but does not
    require to specify the full output size---either the target width or heigh will
    suffice, in which case the aspect ratio is preserved.

    More information about the resampling filters can be found at
    https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-filters

    Parameters
    ----------
    image : PIL.Image.Image
        The original image.

    width : int
        The target image width (if not provided it is determined by the target
        height preserving the aspect ratio).

    height : int
        The target image height (if not provided it is determined by the target
        width preserving the aspect ratio).

    resample
        An optional resampling filter. This can be one of Resampling.NEAREST,
        Resampling.BOX, Resampling.BILINEAR, Resampling.HAMMING, Resampling.BICUBIC
        or Resampling.LANCZOS.

    box : tuple[float, float, float, float]
        An optional 4-tuple of floats providing the source image region to be scaled.
        The values must be within (0, 0, width, height) rectangle. If omitted or
        None, the entire source is used.

    reducing_gap : float
        Apply optimization by resizing the image in two steps. First, reducing the
        image by integer times using `reduce()``. Second, resizing using regular resampling.
        The last step changes size no less than by `reducing_gap times`. `reducing_gap`
        may be None (no first step is performed) or should be greater than 1.0.
        The bigger `reducing_gap`, the closer the result to the fair resampling.
        The smaller `reducing_gap`, the faster resizing. With `reducing_gap` greater
        or equal to 3.0, the result is indistinguishable from fair resampling in
        most cases.

    Returns
    -------
    PIL.Image.Image
        The resized image.
    """
    # pylint: disable=too-many-arguments
    # If we are not providing neither the target width nor the target height
    # there is nothing we can do except giving up.
    if width is None and height is None:
        raise RuntimeError('Please provide at least one length to resize the image.')
    original_width, original_height = image.size
    # If only one parameter is provided, then we calculate the other by preserving
    # the aspect ratio, and we effectively resize to width...
    if height is None:
        height = round(width / original_width * original_height)
    # ...or to height.
    elif width is None:
        width = round(height / original_height * original_width)
    # And now we are good to go.
    logger.info(f'Resizing image {original_width} x {original_height} -> {box} '
        f'-> {width} x {height}...')
    return image.resize((width, height), resample, box, reducing_gap)


def crop_image(image: PIL.Image.Image, rectangle: Rectangle) -> PIL.Image.Image:
    """Crop an image to a given rectangle.

    Parameters
    ----------
    image : PIL.Image.Image
        The original image

    rectangle : Rectangle
        The rectangle delimiting the cropping area

    Returns
    -------
    PIL.Image.Image
        The cropped image.
    """
    width, height = image.size
    logger.info(f'Cropping image {width} x {height} -> {rectangle}...')
    return image.crop(rectangle.bounding_box())


# def autocrop_image(image: PIL.Image.Image) -> PIL.Image.Image:
#     """
#     """
#     pass
#
#
# def pad_image(image: PIL.Image.Image, aspect_ratio: float) -> PIL.Image.Image:
#     """
#     """
#     pass


def elliptical_mask(image: PIL.Image.Image) -> PIL.Image.Image:
    """Create an elliptical mask for a given image.

    This is shamelessly borrowed from https://stackoverflow.com/questions/890051

    Parameters
    ----------
    image : PIL.Image.Image
        The input image.

    Returns
    -------
    PIL.Image.Image
        The mask.
    """
    width, height = image.size
    # Here L is 8-bit pixels, grayscale, see
    # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
    mask = PIL.Image.new('L', (width, height), 0)
    PIL.ImageDraw.Draw(mask).ellipse((0, 0, width - 1, height - 1), fill=255, width=0)
    return mask


@dataclasses.dataclass
class Tiling:

    """Small convenience class representing a tiling.
    """

    num_cols: int
    num_rows: int
    image_size: Tuple[int, int]
    tiling_dict: dict = None

    def __post_init__(self) -> None:
        """Post-initialization
        """
        if self.tiling_dict is None:
            self.tiling_dict = {}


def optimal_rectangular_tiling(num_images: int, tile_width: int, tile_height: int = None,
    tile_padding: int = 0, aspect_ratio: float = 1.414) -> Tiling:
    """Calculate the optimal rectangular tiling to be used to arrange a given number
    of images into a rectangular mosaic with the given approximate aspect ratio.

    Parameters
    ----------
    num_images : int
        The number of input images to be tiles.

    tile_width : int
        The width of the single tile.

    tile_height : int
        The height of the single tile.

    tile_padding : int
        The padding between adjacent tiles, in both the horizontal and vertical directions.

    aspect_ratio : float
        The approximate aspect ratio of the final, tiled image.

    Returns
    -------
    Tiling
        A dictionary  of the form {image_id: (posx, posy)} to be used to tile the
        output image.
    """
    # pylint: disable=too-many-locals
    if tile_height is None:
        tile_height = tile_width
    logger.info(f'Creating optimal rectangular tiling for {num_images} '
        f'{tile_width} x {tile_height} images, with target aspect ratio {aspect_ratio}...')
    num_cols = round(np.sqrt(aspect_ratio * num_images * tile_height / tile_width) + 0.5)
    num_rows = round(num_images / num_cols + 0.5)
    num_tiles = num_cols * num_rows
    if num_tiles < num_images:
        raise RuntimeError(f'{num_tiles} tiles are not enough for {num_images} images, '
            'this is most likely a bug in optimal_rectangular_tiling()')
    width = num_cols * (tile_width + tile_padding + 1)
    height = num_rows * (tile_height + tile_padding + 1)
    logger.debug(f'Optimal tiling is {num_cols} x {num_rows} = {num_tiles} tiles, '
        f'overall size for the target image is {width} x {height}.')
    # Calculate the actual tiling...
    tile_permutation = random.sample(range(num_tiles), num_tiles)
    tiling = Tiling(num_cols, num_rows, (width, height))
    for i in range(num_tiles):
        col = i % num_cols
        row = i // num_cols
        index = tile_permutation[i]
        if index < num_images:
            posx = col * (tile_width + tile_padding) + tile_padding
            posy = row * (tile_height + tile_padding) + tile_padding
            tiling.tiling_dict[index] = (posx, posy)
    return tiling
