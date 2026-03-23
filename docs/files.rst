.. _program:

Program Description
===================

``pisameet`` is entirely driven through an excel configuration file, and this
section describes its structure.


Main Configuration File
-----------------------

The main excel configuration file needs to include a tab called ``Program``,
listing all the conference sessions. The basic session information includes an
alphanumeric session identifier, the session name and the date and time for
the start and the end of the session itself, as indicated in the example
below.

.. note::

   The format string for date and time should be ``'%d/%m/%Y %H:%M'``

.. code-block::

   Session ID Session Name  Start Date        End Date
   S1         Session A     22/05/2022 08:00  22/05/2022 12:00
   S2         Session B     22/05/2022 14:00  22/05/2022 18:00

The poster contributions for each session should be listed in separate
sheets, `each named after the unique session identifier` (in the case of the
example above, e.g., we expect to have separate ``S1`` and ``S2`` excel sheets).
Each of the session sheets might look similar to

.. code-block::

   Poster ID   Screen ID   Title            First Name   Last Name   Affiliation
   121         0           Contribution A   Name         Surname     Affiliation A
   144         0           Contribution B   Name         Surname     Affiliation B

More specifically: each posted should be accompanied by a unique identifier,
the identifier of the screen it is going to be shown of, as well as the name,
surname and affiliation of the presenter.

.. warning::

   The posters come with at least two natural, different unique identifiers: the
   one assigned at submission time, and the one attached at the contribution after
   the acceptance. The only thing that we care about is that the names of all
   relevant files for a give poster start with the poster identifier in the
   configuration file, followed by a pre-determined separator (e.g., 121-poster.pdf),
   because this is the basic mechanism that we use to locate files at runtime.

This specifications for the configuration files were written to streamline the
parsing process---the slideshow program can identify the relevant session(s)
by its start and end dates, and only parse the relevant sheets of the excel files.


Ancillary Folder Structure
--------------------------

In order to simplify the process of aggregating information, the parsing
code is quite strict about the folder structure it is expecting. Particularly,
`all the presentation material should live in properly-named folders at the
same level of the configuration file`, e.g.:

.. code-block::

   [lbaldini@pclbaldini docs]$ ls pm2018/
   pm2018.xlsx  poster_images  poster_original  presenters  qrcodes

More specifically:

* ``poster_original`` should include all the (presumably pdf) files with the
  original posters loaded on indico;
* ``poster_images`` should include all the posters, converted to .png format
  in order to be loaded in the slideshow GUI;
* ``presenters`` should include all the pictures of the presenters---note the
  code will be forgiving about this and will happily display an empty pixmap
  if a picture is missing;
* ``qrcodes`` will include the QR code images with the link to the pdf version
  of the poster on indico.

.. warning::

   All the files names inside the aforementioned folder, as stated above,
   should begin with the unique identifier of the poster, followed by a
   well-defined separator.

The poster images and the QR code are automatically generated as
explained in the section about :ref:`preproc`.
