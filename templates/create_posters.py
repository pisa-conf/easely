#!/usr/bin/env python3
#
# Copyright (C) 2021, luca.baldini@pi.infn.it
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


import os
import subprocess

__ROOT = os.path.dirname(os.path.abspath(__file__))


TEMPLATE_PATH = os.path.join(__ROOT, 'poster_template.tex')


def create_poster(screen_id, poster_id):
    """
    """
    tex_file_path = os.path.join(__ROOT, f'{screen_id:02d}_{poster_id:02d}_poster.tex')
    with open(tex_file_path, 'w') as tex_file:
        for line in open(TEMPLATE_PATH, 'r'):
            if line.startswith(r'\newcommand{\screenid}'):
                line = '\\newcommand{\\screenid}{%d}\n' % screen_id
            if line.startswith(r'\newcommand{\posterid}'):
                line = '\\newcommand{\\posterid}{%d}\n' % poster_id
            tex_file.write(line)
    subprocess.call(['pdflatex', tex_file_path])
    subprocess.call(['pdflatex', tex_file_path])
    subprocess.call(['rm', tex_file_path])
    subprocess.call(['rm', tex_file_path.replace('.tex', '.aux')])
    subprocess.call(['rm', tex_file_path.replace('.tex', '.log')])
    src = tex_file_path.replace('.tex', '.pdf')
    dest = tex_file_path.replace('.tex', '.png')
    subprocess.call(['convert', src, dest])



if __name__ == '__main__':
    for screen in (1, 2):
        for poster in (0, 1, 2, 3):
            create_poster(screen, poster)
