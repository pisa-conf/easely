.. _schema:

:mod:`~easely.schema` --- Excel schema
======================================

The entire poster display system is driven by a single excel file, encapsulating
all the information about the timing and content of the poster sessions, as
well as which posters get to be displayed on which screens.

The typical workflow is as follows:

* an empty skeleton of the excel configuration file is automatically generated
  based on the information on indico;
* the generated file is then edited by hand, most notably with the mapping between
  the host names of the devices driving the screens and the screens themselves,
  as well as the mapping between the posters and the screens;
* the file is read and applied by all the GUI applications to run the actual
  display.

This module contains the basic schemas of the relevant excel woorksheets, and
is the unique source of truth in both write and read mode.

.. literalinclude:: ../src/easely/schema.py
   :pyobject: program_schema

.. literalinclude:: ../src/easely/schema.py
   :pyobject: hosts_schema

.. literalinclude:: ../src/easely/schema.py
   :pyobject: session_schema


Module documentation
--------------------

.. automodule:: easely.schema