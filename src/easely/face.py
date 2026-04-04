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


"""Face-detection and cropping facilities.
"""

import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import List

import cv2
import numpy as np
import PIL.ImageDraw
import PIL.ImageFont

from .img2 import Rectangle, elliptical_mask, open_image, resize_image, save_image
from .logging_ import logger
from .paths import sanitize_file_path
from .typing_ import PathLike


# Path to the folder containing all the opencv model files.
_DATA_DIR = pathlib.Path(__file__).parent.parent.parent / "data"
_CASCADE_FILE_PATH = _DATA_DIR / "haarcascade_frontalface_default.xml"
_YUNET_FILE_PATH = _DATA_DIR / "face_detection_yunet_2023mar.onnx"


class FaceDetection(str, Enum):

    """Small Enum class with the available face-detection models.
    """

    CASCADE = "cascade"
    YUNET = "yunet"


def _read_image(file_path: PathLike) -> np.ndarray:
    """Run ``cv2.imread()`` on a given file path.

    This is a generic helper function for all the open-cv face-detection algorithms.

    Arguments
    ----------
    file_path : PathLike
        The path to the image file.

    Returns
    -------
    np.ndarray
        The image as a NumPy array.
    """
    file_path = sanitize_file_path(file_path, check_exists=True)
    image = cv2.imread(f"{file_path}")
    if image is None:
        raise RuntimeError(f"Could not read image file {file_path}")
    return image


@dataclass
class Box(Rectangle):

    """Wrapper around the Rectangle class, representing a bounding box from face detection.

    In addition to the basic rectangle properties, this container keeps track of
    all the stuff that we need in order to sort the face-detection candidates and
    select the best one (e.g., the fractional area within the original image, and
    any score metrics from the face-detection algorithm itself).

    Arguments
    ---------
    x0 : int
        The x coordinate of the top-left corner of the rectangle.

    y0 : int
        The y coordinate of the top-left corner of the rectangle.

    width : int
        The width of the rectangle.

    height : int
        The height of the rectangle.

    fractional_area : float
        The area of the rectangle as a fraction of the original image area.

    score : float
        The confidence score of the face detection, if available (1.0 if not).
    """

    fractional_area: float
    score: float = 1.

    def quality(self) -> float:
        """Empirical quality factor for sorting the candidate face-detection boxes.
        """
        return np.sqrt(self.fractional_area) * self.score

    def __lt__(self, other) -> bool:
        """Overloaded comparison operator.
        """
        return self.quality() < other.quality()


def run_cascade(file_path: PathLike, min_fractional_area: float = 0.02,
    scale_factor: float = 1.1, min_neighbors: int = 2) -> List[Box]:
    """Minimal wrapper around the standard opencv face detection, see, e.g,
    https://www.datacamp.com/tutorial/face-detection-python-opencv

    Internally this is creating a ``cv2.CascadeClassifier`` object based on a suitable
    model file for face detection, and running a ``detectMultiScale`` call with
    the proper parameters. The output rectangles containing the candidate faces,
    which are returned by opencv as simple (x, y, width, height) tuples, are
    converted into :class:`Box` objects, and the list of boxes is sorted
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

    min_fractional_area : float
        The minimum area of the output rectangle as a fraction of the original image
        area. Objects smaller than that are ignored. This is converted internally to
        an actual size in pixels and passed as the ``minSize`` parameter to the
        ``detectMultiScale`` call.

    scale_factor : float
        Parameter specifying how much the image size is reduced at each image scale
        (passed along verbatim as ``scaleFactor`` to the ``detectMultiScale`` call).

    min_neighbors : int
        Parameter specifying how many neighbors each candidate rectangle should
        have to retain it (passed along verbatim as ``minNeighbors`` to the
        ``detectMultiScale`` call).

    Returns
    -------
    list[Box]
        The list of :class:`Box` objects containing the face candidates.
    """
    image = cv2.cvtColor(_read_image(file_path), cv2.COLOR_BGR2GRAY)
    height, width = image.shape
    model = cv2.CascadeClassifier(f"{_CASCADE_FILE_PATH}")
    # Calculate the minimum size in pixels for the output square.
    min_side = int(np.sqrt(height * width * min_fractional_area))
    # Run the actual face-detection code.
    candidates = model.detectMultiScale(image, scaleFactor=scale_factor,
        minNeighbors=min_neighbors, minSize=(min_side, min_side))
    boxes = []
    for candidate in candidates:
        x, y, w, h = (int(value) for value in candidate)
        fractional_area = w * h / (height * width)
        score = 1.
        boxes.append(Box(x, y, w, h, fractional_area, score))
    boxes.sort(reverse=True)
    return boxes


def run_yunet(file_path: PathLike, min_fractional_area: float = 0.02,
    score_threshold: float = 0.7, nms_threshold: float = 0.3,
    top_k: int = 5000) -> List[Box]:
    """Run the YuNet face detection model.

    The YuNet outout is of the form ``[x, y, w, h, l0x, l0y, ..., l4x, l4y, score]``
    and we are basically interested in the first four values for the bounding box,
    and the last one for the confidence score.

    Arguments
    ---------
    file_path : PathLike
        The path to input image file.

    min_fractional_area : float
        The minimum area of the detected face bounding box as a fraction of the original
        image area. Objects smaller than that are ignored.

    score_threshold : float
        The confidence score threshold for the face detection (0--1). This simply
        filters out all the candidates below a given threshold.

    nms_threshold : float
        The non-maximum suppression threshold for the face detection. This
        is meant to remove duplicate overlapping boxes for the same face, which are
        commonly predicted by the model. Lower value (e.g. 0.3) imply a more aggressive
        removal, with fewer duplicates, while higher values (e.g. 0.7) keeps more
        boxes, at the risk of duplicates.

    top_k : int
        The maximum number of candidates to consider before non-maximum suppression.
        The model may produce thousands of raw detections, and ``top_k`` keeps only
        the best K by score before suppression. Lower values result in shorter running
        times, but you might miss faces in crowded scenes; higher is safer, but
        slower on average.

    Returns
    -------
    list[Box]
        The list of :class:`Box` objects containing the face candidates.
    """
    image = _read_image(file_path)
    height, width, _ = image.shape
    model = cv2.FaceDetectorYN.create(_YUNET_FILE_PATH, "", (width, height), score_threshold,
        nms_threshold, top_k)
    # Run the actual face-detection code.
    _, candidates = model.detect(image)
    # Note the face detection returns None if no face is found.
    if candidates is None:
        return []
    boxes = []
    for candidate in candidates:
        x, y, w, h = (int(value) for value in candidate[:4])
        score = candidate[-1]
        fractional_area = w * h / (height * width)
        # Note the filtering on the minimum fractional area needs to be done by hand.
        if fractional_area >= min_fractional_area:
            boxes.append(Box(x, y, w, h, fractional_area, score))
    boxes.sort(reverse=True)
    return boxes


def run_face_detection(file_path: PathLike, model: FaceDetection,
    min_fractional_area: float = 0.02, **kwargs) -> List[Box]:
    """Run the face detection on the input image, with the specified model and parameters.

    Arguments
    ---------
    file_path : PathLike
        The path to input image file.

    model : FaceDetection
        The face-detection model to use. This is an Enum with the available models,
        and it is meant to be extended in the future as we add more models.

    min_fractional_area : float
        The minimum area of the detected face bounding box as a fraction of the original
        image area. Objects smaller than that are ignored.

    **kwargs
        Optional keyword arguments to be passed to the actual face-detection function,
        depending on the model. See the documentation of the specific functions for
        details on what parameters are accepted.
    """
    if model == FaceDetection.CASCADE:
        runner = run_cascade
    elif model == FaceDetection.YUNET:
        runner = run_yunet
    else:
        raise RuntimeError(f"Unknown face-detection model {model}")
    logger.info(f"Running face detection on {file_path} with {model} ({kwargs})...")
    boxes = runner(file_path, min_fractional_area, **kwargs)
    logger.info(f"Done, {len(boxes)} candidate box(es) found.")
    for i, box in enumerate(boxes):
        logger.debug(f"Candidate {i + 1}: {box}")
    return boxes


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
    rectangle = rectangle.isoarea_square()
    # First of all, pad the rectangle on the four sides as intended.
    logger.debug("Running rectangle-padding step to identify crop area...")
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
    logger.info(f"Padded rectangle too large for the {image_width} x {image_height} image...")
    rectangle.width = rectangle.height = min(image_width, image_height)
    rectangle.x0 = rectangle.x0 - (rectangle.width - rectangle.width) // 2
    rectangle.y0 = rectangle.y0 - (rectangle.height - rectangle.height) // 2
    rectangle = rectangle.shift_to_fit(image_width, image_height)
    logger.debug(f"Cropping area refined to {rectangle}.")
    return rectangle


def crop_face(file_path: PathLike, output_file_path: PathLike, size: int,
    circular_mask: bool = False, model: FaceDetection = FaceDetection.CASCADE,
    min_fractional_area: float = 0.02, detect_kwargs: dict = None,
    enlarge_kwargs: dict = None, interactive: bool = False, overwrite: bool = False) -> PathLike:
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

    model : FaceDetection
        The face-detection model to use.

    min_fractional_area : float
        The minimum area of the detected face bounding box as a fraction of the original
        image area. Objects smaller than that are ignored.

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
        logger.info(f"Output file {output_file_path} already exists, skipping...")
        return
    detect_kwargs = detect_kwargs or {}
    enlarge_kwargs = enlarge_kwargs or {}
    try:
        candidates = run_face_detection(file_path, model, min_fractional_area, **detect_kwargs)
    except RuntimeError as exception:
        logger.error(f"{exception}, giving up on this one...")
        return
    num_candidates = len(candidates)
    image = open_image(file_path)
    # If there is no candidate bbox, we make a square one up.
    if num_candidates == 0:
        logger.warning(f"No face candidate found in {file_path}, picking generic square...")
        candidates.append(Rectangle.square_from_size(*image.size))
    # In case there are multiple candidates, we pick the largest one.
    if num_candidates > 1:
        logger.warning(f"Multiple face candidates found in {file_path}, picking first...")
    # Go on with the best face candidate.
    original_rectangle = candidates[0]
    final_rectangle = enlarge_rectangle(original_rectangle, *image.size, **enlarge_kwargs)
    if interactive:
        # For debugging purposes, we offer some insight into the face-detection process.
        draw = PIL.ImageDraw.Draw(image)
        font_size = int(image.width * 0.02)
        font = PIL.ImageFont.truetype("DejaVuSans.ttf", font_size)
        # Draw all the candidate rectangles (if any) in blue...
        for i, rectangle in enumerate(candidates):
            draw.rectangle(rectangle.bounding_box(), outline="blue", width=2)
            x, y = rectangle.x0 + font_size, rectangle.y0 + font_size
            draw.text((x, y), f"{i}", font=font)
        # ... and the final, optimized rectangle in red.
        draw.rectangle(final_rectangle.bounding_box(), outline="red", width=2)
        image.show()
    image = resize_image(image, size, size, box=final_rectangle.bounding_box())
    if circular_mask:
        image.putalpha(elliptical_mask(image))
    save_image(image, output_file_path)
    return output_file_path