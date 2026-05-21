.. _pdf:

:mod:`~easely.pdf` --- PDF rasterization
========================================

This module contains utilities to transform PDF files into rasterized images, which is
what we actually display on the system screens.

The main function of the module is :func:`~easely.pdf.pdf_to_png`, which provides a
common interface to the different rasterization tools that we support, and is the one
that is exposed through the main command-line interface. Internally, the actual
rasterization is performed by one of the following tools:

* `ImageMagick <https://imagemagick.org/>`_, which is a very popular command-line tool
  for image manipulation, and was the first conversion path to be implemented (note this
  requires a working image magick installation);
* `PyMuPDF <https://pymupdf.readthedocs.io/en/latest/>`_, which is a Python binding for
  the MuPDF library, a lightweight PDF and XPS viewer;
* `pdf2image <https://pdf2image.readthedocs.io/en/latest/>`_, which is another Python
  library for PDF manipulation (note this requires a working poppler installation at
  run time).

When you start rasterizing many posters, you will realize that they come in many different
flavors, produced with all sort of different tools, and you will run in edge cases with
any of the available tools, i.e., there is no silver bullet. Hopefully one of the three
will make the trick---good luck!


Module documentation
--------------------

.. automodule:: easely.pdf