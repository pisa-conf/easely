.. _img:

:mod:`~easely.img` --- Image Processing
=======================================

This module provides functions to operate with rasterized images, and is used
for the poster rasterization and for the face detection tasks, among other things.

More specifically, the module provides the following wrappers around the basic
functions of the Pillow library:

* :meth:`~easely.img.open_image`
* :meth:`~easely.img.save_image`
* :meth:`~easely.img.resize_image`
* :meth:`~easely.img.crop_image`
* :meth:`~easely.img.autocrop_image`
* :meth:`~easely.img.pad_image`

In addition, a :class:`~easely.img.Rectangle` class is provided, intended to help
with all the operations related to bounding boxes, such as those used for face
detection.


Module documentation
--------------------

.. automodule:: easely.img