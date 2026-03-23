# Copyright (C) 2021--2026 the easely team.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Minimal __init__ file.
"""

import pathlib
import subprocess

from ._version import __version__ as __base_version__


def _git_suffix() -> str:
    """If we are in a git repo, we want to add the necessary information to the
    version string.

    This will return something along the lines of ``+gf0f18e6.dirty``.
    """
    # pylint: disable=broad-except
    kwargs = dict(cwd=pathlib.Path(__file__).parent, stderr=subprocess.DEVNULL)
    try:
        # Retrieve the git short sha to be appended to the base version string.
        args = ["git", "rev-parse", "--short", "HEAD"]
        sha = subprocess.check_output(args, **kwargs).decode().strip()
        suffix = f"+g{sha}"
        # If we have uncommitted changes, append a `.dirty` to the version suffix.
        args = ["git", "diff", "--quiet"]
        if subprocess.call(args, stdout=subprocess.DEVNULL, **kwargs) != 0:
            suffix = f"{suffix}.dirty"
        return suffix
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""


__version__ = f"{__base_version__}{_git_suffix()}"


import os
# import shutil
# import sys

# #
# # System-wide environment settings.
# #
PACKAGE_NAME = 'easely'
PISAMEET_ROOT = os.path.abspath(os.path.dirname(__file__))
PISAMEET_BASE = os.path.abspath(os.path.join(PISAMEET_ROOT, os.pardir, os.pardir))
PISAMEET_DATA = os.path.join(PISAMEET_BASE, 'data')
PISAMEET_GRAPHICS = os.path.join(PISAMEET_BASE, 'graphics')

MISSING_PICTURE_PATH = os.path.join(PISAMEET_GRAPHICS, 'unknown_female.png')
MISSING_POSTER_PATH = os.path.join(PISAMEET_GRAPHICS, 'pisameet2024.png')
MISSING_QRCODE_PATH = os.path.join(PISAMEET_GRAPHICS, 'unknown_qrcode.png')

# Magic file to induce a reload in the apps that support it.
MAGIC_FILE_PATH = os.path.join(PISAMEET_BASE, '.reload')



def read_magic_file():
    """
    """
    if os.path.exists(MAGIC_FILE_PATH):
        logger.info('Magic file found!')
        os.remove(MAGIC_FILE_PATH)
        logger.info('Magic file removed.')
        return 1
    return 0
