.. _face:

:mod:`~easely.face` --- Face Recognition
========================================

This module provides a few utilities for doing face recognition on image files, with
the main purpose of cropping the images that the presenter provides turning them
into square headshots that can be displayed on the system screens.

More specifically:

* :func:`~easely.face.run_face_recognition` runs the opencv face recognition and
  returns a list of :class:`~easely.img2.Rectangle` objects corresponding to the face
  candidates found in the image; these are typically very tight, and therefore
* :func:`~easely.face.enlarge_rectangle` is designed to post-process a given
  rectangle from opencv into the best square within the original image that
  contains the face with enough margin;
* :func:`~easely.face.crop_face` is the main function of the module, which
  wraps everything together and process a given image file into the corresponding
  cropped headshot.


Module documentation
--------------------

.. automodule:: easely.face