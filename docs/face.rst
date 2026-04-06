.. _face:

:mod:`~easely.face` --- Face Detection
======================================

This module provides a few utilities for doing face detection on image files, with
the main purpose of cropping the images that the presenter provides turning them
into square headshots that can be displayed on the system screens.

More specifically, :func:`~easely.face.crop_face` is the main function of the module,
which wraps everything together into a common interface and process a given image
file into the corresponding cropped headshot. Internally, the process happens in two steps:

* first the actual face detection is performed, leveraging the facilities provided by
  the `opencv <https://opencv.org/>`_ library; note that the actual opencv call are
  wrapped into the thin layer :func:`~easely.face.run_face_detection`, which
  unifies the interface across different face-detection models and transforms the
  output into a list of :class:`~easely.face.Box` objects;
* then the best candidate box is selected and post-processed into the final square
  to be used for cropping, and the actual headshot is generated and saved to the output
  file.


Available models
----------------

The module currently supports two different face-detection models, which can be
selected via the ``model`` parameter of :func:`~easely.face.crop_face`: (or, equivalently,
via the same option from the main command-line interface):

* :attr:`~easely.face.FaceDetection.CASCADE`, which is the traditional Haar-cascade-based
  face detection model provided by opencv; this is the default model, and it is very
  fast. (See https://docs.opencv.org/4.x/db/d28/tutorial_cascade_classifier.html
  for more information);
* :attr:`~easely.face.FaceDetection.YUNET`, which is a more modern face-detection model
  based on a convolutional neural network; this is somewhat slower, but performs better
  in some cases. (See https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
  for more information.)

If you do process lots of images in batch, you will realize that there isn't a single
setup that handles all the edge cases without manual interventions. (Especially when
a presenter sends you a `close-up` picture which is taken in Antarctica, from very far
away, with glasses and helmet on, and a polar bear in the background.)

In cases when things do not quite work out as expected, your best bet is to switch
between the two models and/or change the ``min_fractional_area`` parameter, which controls
the minimum size of the box containing the detected face. You can run the thing into
interactive mode (with the ``--interactive`` flag) to get some insights into the
face-detection process and understand better what is going wrong.

.. warning::

   Each face-detection model has its own parameters, but these are not yet
   exposed through the public API. We could implement that in the future, if it turns
   out that this would be useful.


Module documentation
--------------------

.. automodule:: easely.face