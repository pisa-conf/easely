# Copyright (C) 2026 the easely team.
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


"""Face-recognition and cropping facilities.
"""

import pathlib

import cv2
import PIL.ImageDraw

from .img2 import Rectangle, elliptical_mask, open_image, resize_image, save_image
from .logging_ import logger
from .paths import sanitize_file_path
from .typing_ import PathLike

__all__ = ["run_face_recognition", "enlarge_rectangle", "crop_face"]


_DEFAULT_FACE_DETECTION_MODEL_PATH = pathlib.Path(cv2.data.haarcascades) /\
    "haarcascade_frontalface_default.xml"


def run_face_recognition(file_path: PathLike, scale_factor: float = 1.1,
    min_neighbors: int = 2, min_size: float = 0.15) -> list[Rectangle]:
    """Minimal wrapper around the standard opencv face recognition, see, e.g,
    https://www.datacamp.com/tutorial/face-detection-python-opencv

    Internally this is creating a ``cv2.CascadeClassifier`` object based on a suitable
    model file for face recognition, and running a ``detectMultiScale`` call with
    the proper parameters. The output rectangles containing the candidate faces,
    which are returned by opencv as simple (x, y, width, height) tuples, are
    converted into :class:`Rectangle` objects, and the list of rectangle is sorted
    according to the corresponding area from the smallest to the largest to help
    with the selection process downstream.

    Note that this is producing squares (since apparently this is the way the default
    model we are using was trained) that are only big enough to cover the visible
    part of the face, and if you use this to crop a large image to the person face
    it is very likely that you will want to add some padding on the four sides,
    and especially on the top, which empirically seems to be the most overlooked
    part of the face.

    The ``min_neighbors`` parameter has an important effect on the results and
    should be set on a case-by-case basis. The cascade classifier applies a sliding
    window through the image, and initially it will capture a large number of false
    positives. This parameter specifies the number of neighboring rectangles that
    need to be identified for an object to be considered a valid detection: a value
    of 0 is idiotic, and it will likely return an enormous number of (possibly
    overlapping) rectangles. Small values will yield comparatively more false positives.
    I would say 2 is the absolute minimum one might consider using, and something
    around 5 is more germane to what is commonly found in tutorials online.

    Parameters
    ----------
    file_path : PathLike
        The path to input image file.

    scale_factor : float
        Parameter specifying how much the image size is reduced at each image scale
        (passed along verbatim as ``scaleFactor`` to the ``detectMultiScale`` call).

    min_neighbors : int
        Parameter specifying how many neighbors each candidate rectangle should
        have to retain it (passed along verbatim as ``minNeighbors`` to the
        ``detectMultiScale`` call).

    min_size : float
        Minimum possible fractional object size. Objects smaller than that are ignored.
        This is converted internally to an actual size in pixels, corresponding
        to a square whose side is the geometric mean of the original width and height,
        multiplied by the parameter value.

    Returns
    -------
    list[Rectangle]
        The list of :class:`Rectangle` objects containing the face candidates.
    """
    file_path = sanitize_file_path(file_path, check_exists=True)
    # Create a CascadeClassifier object with the proper model file (and the file
    # path must be a string, not a Path, here).
    classifier = cv2.CascadeClassifier(f'{_DEFAULT_FACE_DETECTION_MODEL_PATH}')
    settings = dict(scale_factor=scale_factor, min_neighbors=min_neighbors, min_size=min_size)
    logger.info(f'Running face detection on {file_path} with {settings}...')
    image = cv2.imread(f'{file_path}')
    if image is None:
        raise RuntimeError(f'Could not read image file {file_path}')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Calculate the minimum size of the output rectangle as that of a square whose
    # side is the geometric mean of the original width and height, multiplied by
    # the min_size input parameter.
    side = Rectangle.rounded_geometric_mean(*image.shape, scale=min_size)
    min_size = (side, side)
    logger.debug(f'Minimum rectangle size set to {min_size}.')
    # Run the actual face-detection code.
    boxes = classifier.detectMultiScale(image, scaleFactor=scale_factor,
        minNeighbors=min_neighbors, minSize=min_size)
    # Convert the output to a list of Rectangle objects, and sort by area.
    logger.info(f'Done, {len(boxes)} candidate face(s) found.')
    # Not we cast the numpy int types to native Python integers.
    rectangles = [Rectangle(*[int(value) for value in box]) for box in boxes]
    rectangles.sort()
    for i, rectangle in enumerate(rectangles):
        logger.debug(f'Candidate rectangle {i + 1}: {rectangle}')
    return rectangles


def enlarge_rectangle(rectangle: Rectangle, image_width: int, image_height: int,
    horizontal_padding: float = 0.5, top_scale_factor: float = 1.25) -> Rectangle:
    """Massage a given rectangle to make it suitable for cropping a face
    out of an image.

    This is used to transform the candidate rectangle containing the face returned
    by opencv into a proper bounding box to be cropped off the original image,
    which in general we would like to be significantly larger than the face-detection
    output. The process takes place in two steps: first we pad the original rectangle
    based on the input parameters, and then we make the necessary modifications,
    if any, to make the final rectangle fit within the original image. The rule
    of thumb is that if the overall dimensions of the rectangle fit in the original
    image, we keep the width and the height of the rectangle and apply the smallest
    possible shift to the origin so that the cropping area does not extend outside
    the image. When the padded rectangle is too big for the original image, instead,
    we resort to the largest square that can be embedded in the image itself,
    and is approximately centered on the initial rectangle. (The comments in
    code might provide the user a firmer grasp on what is actually happening
    behind the scenes.)

    Parameters
    ----------
    rectangle : Rectangle
        The original rectangle returned by the face-detection stage.

    image_width : int
        The with of the original image.

    image_height : int
        The height of the original image.

    horizontal_padding : float
        The horizontal padding, on either side, in units of the equivalent ]
        square side of the rectangle.

    top_scale_factor : float
        The ratio between the pad on the top and that on the right/left.

    Returns
    -------
    Rectangle
        A new Rectangle object, ready for cropping.
    """
    # We assume that the rectangle out of opencv is square.
    if not rectangle.is_square():
        raise RuntimeError(f'Input rectangle {rectangle} is not square')
    # First of all, pad the rectangle on the four sides as intended.
    logger.debug('Running rectangle-padding step to identify crop area...')
    # Remember that the horizontal padding is referred to the size of the
    # rectangle returned by the face-detection stage...
    right = round(horizontal_padding * rectangle.width)
    # ... the top padding is determined by the corresponding scale factor...
    top = round(top_scale_factor * right)
    # ... and we put on the bottom whatever is left.
    bottom = 2 * right - top
    rectangle = rectangle.pad(top, right, bottom)
    # If the padded rectangle is fitting into the original image, then all we
    # have to do is to make sure that the origin is such that the rectangle
    # itself is actually fully contained in the image---and apply a simple shift
    # if that is not the case.
    if rectangle.fits_within(image_width, image_height):
        return rectangle.shift_to_fit(image_width, image_height)
    # And here comes all the fun, as we do have to do our best to get a good
    # face crop when the embedding image is not as large as we would have wanted.
    # After some trial and error I think the best we can do, here, is to
    # pick the largest square fitting into the original image and centered
    # on the rectangle returned by opencv.
    logger.info(f'Padded rectangle too large for the {image_width} x {image_height} image...')
    rectangle.width = rectangle.height = min(image_width, image_height)
    rectangle.x0 = rectangle.x0 - (rectangle.width - rectangle.width) // 2
    rectangle.y0 = rectangle.y0 - (rectangle.height - rectangle.height) // 2
    rectangle = rectangle.shift_to_fit(image_width, image_height)
    logger.debug(f'Cropping area refined to {rectangle}.')
    return rectangle


def crop_face(file_path: PathLike, output_file_path: PathLike, size: int,
    circular_mask: bool = False, detect_kwargs: dict = None, enlarge_kwargs: dict = None,
    interactive: bool = False, overwrite: bool = False) -> PathLike:
    """Produce a square, cropped version of the input image, suitable for use as a headshot
    (i.e., cropped around the face of the person in the image).

    This is running a simple face detection based on opencv, and then adapting
    the best candidate bounding box to produce the final square cropping area.

    Arguments
    ---------
    file_path : PathLike
        The path to the input image file.

    output_file_path : PathLike
        The path where the cropped image will be saved.

    size : int
        The size of the output image (square).

    circular_mask : bool, optional
        Whether to apply a circular mask to the output image.

    interactive : bool, optional
        Whether to display the image with bounding boxes for debugging.

    detect_kwargs : dict, optional
        Optional keyword arguments to be passed to the face detection function.

    enlarge_kwargs : dict, optional
        Optional keyword arguments to be passed to the rectangle enlargement function.

    Returns
    -------
    PathLike
        The path to the cropped image file, if it was actually created/overwritten,
        of None otherwise.
    """
    output_file_path = sanitize_file_path(output_file_path)
    if output_file_path.is_file() and not overwrite:
        logger.info(f'Output file {output_file_path} already exists, skipping...')
        return
    detect_kwargs = detect_kwargs or {}
    enlarge_kwargs = enlarge_kwargs or {}
    try:
        candidates = run_face_recognition(file_path, **detect_kwargs)
    except RuntimeError as exception:
        logger.error(f'{exception}, giving up on this one...')
        return
    num_candidates = len(candidates)
    image = open_image(file_path)
    # If there is no candidate bbox, we make a square one up.
    if num_candidates == 0:
        logger.warning(f'No face candidate found in {file_path}, picking generic square...')
        candidates.append(Rectangle.square_from_size(*image.size))
    # In case there are multiple candidates, we pick the largest one.
    if num_candidates > 1:
        logger.warning(f'Multiple face candidates found in {file_path}, picking largest...')
    # Go on with the best face candidate.
    original_rectangle = candidates[-1]
    final_rectangle = enlarge_rectangle(original_rectangle, *image.size, **enlarge_kwargs)
    if interactive:
        draw = PIL.ImageDraw.Draw(image)
        draw.rectangle(original_rectangle.bounding_box(), outline='white', width=2)
        draw.rectangle(final_rectangle.bounding_box(), outline='red', width=2)
        image.show()
        input("Press Enter to continue...")
    image = resize_image(image, size, size, box=final_rectangle.bounding_box())
    if circular_mask:
        image.putalpha(elliptical_mask(image))
    save_image(image, output_file_path)
    return output_file_path