.. _release_notes:

Release notes
=============

* Not raising an exception on empty poster rosters.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/45


Version 0.6.5 (2026-05-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Emergency patch for a bug introduced in the previous release.


Version 0.6.4 (2026-05-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Enforcing types (from the underlying shemas) when reading the configuration file.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/44
  - https://github.com/pisa-conf/easely/issues/30


Version 0.6.3 (2026-05-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Widget name added to the poster label, and background color set to white to avoid isses
  with transparency in the poster images.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/42


Version 0.6.2 (2026-05-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Magic file mechanism removed---the reboot is now handled via ansible.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/40
  - https://github.com/pisa-conf/easely/issues/37


Version 0.6.1 (2026-05-16)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* File filtering for indico downloads made case insensitive.
* Missing import in tasks restored.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/39


Version 0.6.0 (2026-05-15)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Default pixmaps for posters, Qr codes and headshots in.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/36
  - https://github.com/pisa-conf/easely/pull/33


Version 0.5.0 (2026-05-04)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* New format for the xlsx configuration file.
* Minimal fixes to get all the three GUI applications up and running again.
* Major restructuring of the GUI code to allow for qss-driven styling and customization.
* ``data``, ``qss`` and ``graphics`` directories moved into ``src``, and marked for
  shipping with the package in the ``pyproject.toml`` file.
* ``importlib.resources`` consistently used to load data files, instead of hardcoding paths.
* Bug fix in the generation of the program excel file.
* Obsolete ``scripts`` and ``templates`` directories removed.
* Documentation updated.
* Pull requests merged and issues closed:

  - https://github.com/pisa-conf/easely/pull/28
  - https://github.com/pisa-conf/easely/pull/22
  - https://github.com/pisa-conf/easely/issues/20


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