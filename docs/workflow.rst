.. _workflow:

Workflow
========

This is a top-level description of the workflow to prepare a full conference setup
with ``easely``. The different subsections of this section map directly into the
sub-parsers of the ``easely`` command-line interface, and we shall quickly go
through each one of them.

.. program-output:: easely --help


Folder structure
----------------

By design each conference is supposed to have its own workspace, where all the relevant
files live. If this is your first time using ``easely``, go ahead, create an empty folder
for your conference cd into it and follow the instructions in the next sections.

The workspace will contain a few standard files, along with a folder structure resembling
the one defined in the ``WorkspaceLayout`` class in the ``paths`` module:

.. literalinclude:: ../src/easely/paths.py
   :pyobject: WorkspaceLayout


.. note::

   While the command-line interface allows you to customize the behavior of each task,
   the default values are chosen to fit this folder structure, and you should be good
   by literally following two simple rules: operate (i.e., run ``easely`` tasks) from
   within the root folder of your conference and just let the thing flow.


Downloading the conference data
-------------------------------

The first thing you have to do is to download all the relevant event metadata, as well as
the poster attachments, from the Indico server. This is done with the ``download`` sub-command:

.. program-output:: easely download --help

If you issue, e.g.,

.. code-block:: bash

   cd my-conference-workspace
   easely download https://agenda.infn.it/export/event/37033.json

you should see at the very minimum a ``program.json`` file in the root of your workspace,
containing all the relevant metadata for the conference, such as the list of sessions and
contributions within each session.
If the event has one or more poster sessions with contributions, and if these contributions
have attachments, they will be automatically downloaded in the ``attachments`` folder.

Most likely you will have to repeat this over and over again as you prepare for the
conference---be assured that people will upload material to indico until the very last minute,
and often during the conference itself. We are fully aware that useless downloads are
expensive, and the basic rules for the ``download`` task are the following:

* the json file with the program is overwritten every time, with no mercy;
* we keep track of the indico upload timestamp for each attachment, and we only download
  any given file if it is not already on disk, or if the version on indico is newer than
  the one on disk.

.. note::

   In order to facilitate matching the attachments files with the actual contributions,
   all the file names are prepended with the ``friendly_id`` of the contribution, which
   is an identifier generated based on the submission order that is guaranteed to be
   unique within the scope of the conference.


Creating the poster roster
--------------------------

The very first thing that you will need to do with the json file containing the
conference metadata is to create the poster roster, which is the excel file that drives
all the poster display. This is achieved with the ``roster`` sub-command:

.. program-output:: easely roster --help

Normally, all you have to do is to run the sub-command once from within the
conference workspace

.. code-block:: bash

   easely roster

and this will create a ``program.xlsx`` file alongside the original ``program.json`` file.

If you open the file, you will see a sheet with the list of all the poster sessions, and
a series of additional sheets (one per session) listing all the contributions. This is
very important, as this very excel file regulates two important things:

* the times when the system switches between different poster sessions; and
* the mapping of the contributions to the different screens in the poster display.

.. warning::

   The poster roster, by definition, needs manual editing. You don't want to generate it
   before the conference program is fully finalized, and you do not want to overwrite
   after you have started editing it. (The sub-command will not overwrite it by default.)


Generating the QR codes
-----------------------

By default the poster display system will show a QR code in the upper part of the screen,
containing a link pointing to the contribution on the indico server. This allows
attendees to quickly access the relevant indico page (e.g, with their smartphone)
and download a pdf copy of the poster to their device, if they care.

Specific QR codes for each single posters can be generate with the ``qrcodes`` sub-command:

.. program-output:: easely qrcodes --help

As usual, from within the conference workspace, you can just run

.. code-block:: bash

   easely qrcodes

and there it is: you will have your QR codes in the ``qrcodes`` folder, ready to be
consumed by the poster display applications.

.. note::

   As for most of the final artifact that correspond to a specific contributions,
   QR codes are named after the ``friendly_id`` of the contribution, which is an identifier
   generated based on the submission order that is guaranteed to be unique within the
   scope of the conference.


Dispatching attachments
-----------------------

When you download the indico attachments, by default you will get all the graphics files
(e.g., pdf, png, pptx.) in the default ``attachments`` folder. These will include various
things along with the actual poster files---presenter close-up pictures, mini-elevator
pitches, and any additional material that you might have asked the presenters to upload.

For the purpose of the poster display, we are mainly interested in two types of files:

* the actual poster files, which are supposed to be in pdf format; and
* the presenter close-up pictures, which are supposed to be in a sensible graphics format.

The ``dispatch`` sub-command allows is meant to automatically sort out the attachments
into the ``posters`` and ``headshots`` folders, respectively.

.. program-output:: easely dispatch --help

As usual, from within the conference workspace, you can just run

.. code-block:: bash

   easely dispatch

Unless your conference is tiny (literally: if you have more than half a dozen posters) you
will painfully realize that no matter how precise were the instructions you gave the
presenters, they can be very creative in ignoring your indications. This is an area where
manual intervention will be required during the preparation of the conference, and likely
during the conference itself. For this very reason, the ``dispatch`` task will
never overwrite existing files in the destination folders---there is essentially no good
automatic way to tell whether a file was put there manually for good reasons.

.. warning::

   The current mechanism is not very amenable to frequent changes in the attachments, as
   once the original files have been dispatched once in the destination folder, any
   subsequent change needs to be done manually. This is, admittedly, an area where we
   could improve, but the basic reasoning is that we generally want to keep indico in
   order (e.g, rename files there) at which point we can always regenerate everything
   from scratch right before the beginning of the conference, and treat subsequent
   changes as manual interventions.


Rasterizing the posters
-----------------------

The main task of the command-line interface is to generate rasterized versions of the
posters, which are the actual files that will be displayed on the poster display system.
This is done with the ``rasterize`` sub-command:

.. program-output:: easely rasterize --help

This task is peculiar in a few different ways: it is definitely the one that takes
the longest time to run, especially if you launch it on all the poster contributions
of a large conference---be ready because it might take a while the first time.
In addition, it is one of the tasks where you actually have to pay attention to the
command-line arguments, as best results are obtained when your choices match
your hardware setup.

More specifically, if you adjust the ``target-width`` argument to match `exactly`
the actual width of the ``QPixmap`` objects that are used in the poster display
system, you will be able to display the rasterized posters to the screen without
any additional scaling. This, in turn, depends on both the screen resolution and
the border size that you have decided to use.

Additionally, the task allow to rasterize the input pdf to a (larger) intermediate
png file, which is then resized using a high-quality resampling algorithm to the
final size. This tend to produce better result that rasterizing directly to the
final size, and an intermediate size of twice the final size is a good compromise
between quality and performance.

.. warning::

   The variety of tools used to produce the original pdf files for the poster is
   such that is very difficult not to run in edge cases where the rasterization
   is not optimal (e.g., transparencies are not handled correctly). While we might
   improve on this one, it is very important to check the rasterized output
   on a poster-by-poster basis, and to be ready to intervene manually.


Cropping the headshots
----------------------

Just like for the QR codes, the poster display system will show a headshot image of
the presenter, when available. (As a matter of fact, next to the QR code).
In order for the thing to look nice, you will have to crop all the original
headshot images to a square format, and to resize them making sure that the
cropped image is centered on the actual face. This is achieved with the
``facecrop`` sub-command:

.. program-output:: easely facecrop --help

.. warning::

   The face cropping leverages opencv under the hood and generally does a reasonable
   job at detecting and cropping faces, but there are edge cases where it fails and
   need manual intervention. This is an area where we can definitely improve.