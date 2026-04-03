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

from .img2 import Rectangle, elliptical_mask, open_image, resize_image, save_image
from .logging_ import logger
from .paths import sanitize_file_path
from .typing_ import PathLike


_DEFAULT_FACE_DETECTION_MODEL_PATH = pathlib.Path(cv2.data.haarcascades) /\
    'haarcascade_frontalface_default.xml'


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
    file_path
        The path to input image file.

    scale_factor
        Parameter specifying how much the image size is reduced at each image scale
        (passed along verbatim as ``scaleFactor`` to the ``detectMultiScale`` call).

    min_neighbors
        Parameter specifying how many neighbors each candidate rectangle should
        have to retain it (passed along verbatim as ``minNeighbors`` to the
        ``detectMultiScale`` call).

    min_size
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
    bboxes = classifier.detectMultiScale(image, scaleFactor=scale_factor,
        minNeighbors=min_neighbors, minSize=min_size)
    # Convert the output to a list of Rectangle objects, and sort by area.
    logger.info(f'Done, {len(bboxes)} candidate face(s) found.')
    rectangles = [Rectangle(*bbox) for bbox in bboxes]
    rectangles.sort()
    for i, rectangle in enumerate(rectangles):
        logger.debug(f'Candidate rectangle {i + 1}: {rectangle}')
    return rectangles


def crop_to_face(input_file_path: PathLike, output_file_path: PathLike, size: int,
    circular_mask: bool = False, interactive: bool = False) -> None:
    """
    """
    #options = _process_kwargs(FACE_CROP_VALID_KWARGS, **kwargs)
    #detect_opts = _filter_kwargs('scale_factor', 'min_neighbors', 'min_size', **options)
    #crop_opts = _filter_kwargs('horizontal_padding', 'top-scale-factor', **options)
    #for file_path in file_list:

    detect_opts = {}
    crop_opts = {}
    try:
        candidates = run_face_recognition(input_file_path, **detect_opts)
    except RuntimeError as exception:
        logger.error(f'{exception}, giving up on this one...')
        return
    num_candidates = len(candidates)
    image = open_image(input_file_path)
    # If there is no candidate bbox, we make a square one up.
    if num_candidates == 0:
        logger.warning(f'No face candidate found in {input_file_path}, picking generic square...')
        candidates.append(Rectangle.square_from_size(*image.size))
    # In case there are multiple candidates, we pick the largest one.
    if num_candidates > 1:
        logger.warning(f'Multiple face candidates found in {input_file_path}, picking largest...')
    # Go on with the best face candidate.
    original_rectangle = candidates[-1]
    final_rectangle = original_rectangle.setup_for_face_cropping(*image.size, **crop_opts)
    if interactive:
        draw = PIL.ImageDraw.Draw(image)
        draw.rectangle(original_rectangle.bounding_box(), outline='white', width=2)
        draw.rectangle(final_rectangle.bounding_box(), outline='red', width=2)
        image.show()
    image = resize_image(image, size, size, box=final_rectangle.bounding_box())
    if circular_mask:
        image.putalpha(elliptical_mask(image))
    save_image(image, output_file_path)