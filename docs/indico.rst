.. _indico:

indico
======

This module provides a simple interface to the Indico REST API, which allows you to
retrieve the data of an event, including its sessions and contributions.

The basic workflow is as follows:

* :func:`~easely.indico2.download_event_data` allows you to retrieve all the metadata
  attached to an event, given its URL on indico, and save them to a local .json file
  for later use;
* :class:`~easely.indico2.Event` is the main read interface to the event data, and what
  is actually used downstream.

Internally, all the indico metadata are represented as a small collection of dataclasses,
all inheriting from the abstract base class `IndicoObject`, most notably:

* :class:`~easely.indico2.Presenter`;
* :class:`~easely.indico2.Contribution`;
* :class:`~easely.indico2.Session`;
* :class:`~easely.indico2.Event`.



Module documentation
--------------------

.. automodule:: easely.indico