.. _install:

Installation
============

.. warning::

    This is a work in progress, and the installation instructions are not
    finalized yet. Please check back later for updates.

    The thing should go on pypi soon.


Editable installation
---------------------

When you `develop` (as opposed to `use`) a package, you want to install it
in `editable` mode.

.. code-block:: shell

    pip install -e .

Invoking ``pip`` with the ``-e`` command-line switch will place a special
link in the proper folder pointing back to you local version of the source
files (instead of copying the source tree) so that you will always see the
last version of the code as you modify it, e.g., in the local copy of your
git repository. Needless to say, it is still the ``pyproject.toml`` file that
makes all the magic.

.. note::

    You can achieve the same result by just making sure that the
    ``PYTHONPATH`` environmental variable is pointing to the folder where
    your Python modules live, and in fact you might as well do that. That is
    not necessarily considered a good practice, as it departs completely
    from the installation path of a typical Python package that you use as
    a library, but you should still make sure you understand the basic internals
    of the Python import system.
