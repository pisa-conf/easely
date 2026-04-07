# Copyright (C) 2026, the easely team.
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

"""Basic schema for the main excel configuration file.
"""

from dataclasses import dataclass

# We default to a ISO 8601-like format for the date and time, skipping the internal ``T``
# separator, as well as the timezone information.
DATETIME_FORMAT =  "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Column:

    """Column descriptor.
    """

    key: str
    header: str
    type_: type


@dataclass(frozen=True)
class SheetSchema:

    """Sheet schema descriptor.
    """

    name: str
    columns: tuple[Column, ...]

    def col_headers(self) -> tuple[str, ...]:

        """Return the column headers.
        """

        return tuple(col.header for col in self.columns)


def program_schema() -> SheetSchema:

    """Build the schema for the program sheet.
    """

    return SheetSchema(
        name="Program",
        columns=(
            Column(key="id", header="Session ID", type_=int),
            Column(key="name", header="Session name", type_=str),
            Column(key="start_datetime", header="Session start", type_=str),
            Column(key="end_datetime", header="Session end", type_=str),
        )
    )


def hosts_schema() -> SheetSchema:

    """Build the schema for the hosts sheet.
    """

    return SheetSchema(
        name="Hosts",
        columns=(
            Column(key="hostname", header="Hostname", type_=str),
            Column(key="screen_id", header="Screen ID", type_=int),
        )
    )

def session_schema(session_id: int) -> SheetSchema:

    """Build the schema for a generic session sheet.
    """

    return SheetSchema(
        name=f"{session_id}",
        columns=(
            Column(key="friendly_id", header="Friendly ID", type_=int),
            Column(key="screen_id", header="Screen ID", type_=int),
            Column(key="title", header="Title", type_=str),
            Column(key="first_name", header="First name", type_=str),
            Column(key="last_name", header="Last name", type_=str),
            Column(key="affiliation", header="Affiliation", type_=str),
        )
    )
