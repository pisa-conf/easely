.. _workflow:

Workflow
========

This is a top-level description of the workflow to prepare a full conference setup
with `easely`. The different subsections of this section map directly into the
sub-parsers of the `easely` command-line interface, and we shall quickly go
through each one of them.

.. program-output:: easely --help


Folder structure
----------------

You should end up with a folder structure like the one defined in
the `WorkspaceLayout` class in the `paths` module:

.. literalinclude:: ../src/easely/paths.py
   :pyobject: WorkspaceLayout


Downloading the event data
--------------------------

.. program-output:: easely download --help


Creating the poster roster
--------------------------

.. program-output:: easely roster --help


Generating the QR codes
-----------------------

.. program-output:: easely qrcodes --help