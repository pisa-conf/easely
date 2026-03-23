
Raspberry PI Configuration
==========================




Basic installation
------------------

The SD card that comes with the raspberry PI has
`raspbian <https://www.raspberrypi.com/software/operating-systems/>`_ pre-installed.
You can figure out the particular raspbian version by doing

.. code-block::

   > less /etc/os-release

   PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"
   NAME="Raspbian GNU/Linux"
   VERSION_ID="9"
   VERSION="9 (stretch)"
   ID=raspbian
   ID_LIKE=debian
   HOME_URL="http://www.raspbian.org/"
   SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
   BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs"

In order to update to the latest version, go ahead and download the OS image from the
`raspberry page <https://www.raspberrypi.com/software/operating-systems/>`_
and unzip it.

The community recommends `Etcher <https://www.balena.io/etcher/>`_ to flash the
image onto the SD card, and this is actually quite easy---you download the
binary from the website, change the permissions to make it executable and
run it. (You will need a card reader for the thing to happen.)

.. note::

   Version 11 of raspbian comes with Python 3.9.2 installed, and it seems like
   a good starting point for our purposes.

After the OS installation you might want to do an update:

.. code-block::

   > sudo apt dist-upgrade


Dependencies
------------

The only additional packages that you need, on top of the standard raspbian
Desktop installation, are:

* the Python wrappers to the Qt library for the GUI;
* the pandas framework for parsing the excel configuration file.

.. code-block::

   > sudo apt-get install python3-pyqt5 python3-pandas



Setting up the screen
---------------------

You get control of the screen orientation (e.g., vertical vs. horizontal) through
the `Preferences -> Screen Configuration` dialog. This will open the screen
editor that allows to change the orientation.

Alternatively, you can hack the ``/boot/config.txt``, e.g.

.. code-block::

    display_hdmi_rotate=1

to rotate the screen by 90 degrees (i.e., to the right).


Presentation software
---------------------

In order to clone the repository just do

.. code-block::

   > git clone https://github.com/lucabaldini/pisameet.git

This should come up with a small fictional session from the last edition of the
Pisa Meeting (i.e., the one in 2018). You should be able to run the slideshow
by doing

.. code-block::

   > ./pisameet/slideshow.py pm2018/pm2018.xlsx


Unique Screen Identifier
------------------------

Each Raspberry PI should be assigned a unique screen identifier, in order for
the slideshow code to be able to determine with posters should be added to the
roster on any given machine. This is a achieved through a text configuration
file living in the ``pisameet`` subfolder called ``screen.cfg``.

.. note::

   If the ``pisameet/screen.cfg`` files does not exist, a default one will
   be created, using a copy of the ``pisameet/screen.cfg.sample`` included
   in the distribution. (Note the actual configuration file is included in the
   ``.gitignore`` file). In any event, the file should be edited by hand.

   (And it would be a good thing to have a physical label on the board matching
   the screen identifier of each device.)

.. seealso:: :ref:`program`


Automatic slideshow start
-------------------------

The raspberry PIs should be configured in such a way that they will
automatically start the slideshow at login, and the quickest way to achieve that
is through a .Desktop file to along the lines of

.. code-block::

   [Desktop Entry]
   Type=Application
   Name=Pisa Meeting Slideshow
   Exec=/usr/bin/python3 /home/pi/pisameet/pisameet/slideshow.py /home/pi/pisameet/pm2018/pm2018.xlsx

The ``pisameet`` distribution comes with a ``pisameet.desktop`` sample file
that you can adapt and copy into the ``/home/pi/.config/autostart`` folder
(which, most likely, you will have to create first):

.. code-block::

   > mkdir /home/pi/.config/autostart
   > cp pisameet.desktop /home/pi/.config/autostart
