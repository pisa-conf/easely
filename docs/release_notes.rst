.. _release_notes:

Release notes
=============

* Major restructuring of the GUI code to allow for qss-driven styling and customization.
* ``data``, ``qss`` and ``graphics`` directories moved into ``src``, and marked for
  shipping with the package in the ``pyproject.toml`` file.
* ``importlib.resources`` consistently used to load data files, instead of hardcoding paths.
* Bug fix in the generation of the program excel file.
* Obsolete ``scripts`` and ``templates`` directories removed.
* Documentation updated.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/22
  - https://github.com/pisa-conf/easely/issues/16



Version 0.4.0 (2026-04-06)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Face-detection code refactored and cleaned up.
* New YuNet model added.
* Documentation updated.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/18
  - https://github.com/pisa-conf/easely/issues/16


Version 0.3.0 (2026-04-04)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* New ``face.py`` encapsulating all the face-detection logic.
* ``cropface`` task fully revamped, with a bunch of command-line options added.
* Cleanup of some obsolete stuff.
* Documentation updated.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/17


Version 0.2.0 (2026-04-02)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Initial version of the cleaned-up repo.