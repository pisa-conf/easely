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

from dataclasses import dataclass, field

# We default to a ISO 8601-like format for the date and time, skipping the internal ``T``
# separator, as well as the timezone information.
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT =  f"{DATE_FORMAT} %H:%M:%S"


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


@dataclass(frozen=True)
class DictSheetSchema(SheetSchema):

    """Sheet schema descriptor for sheets that are expected as key-value pairs.

    The information is organized with a simple, two-column layout where the
    first column contains the key and the second contains the corresponding value.
    """

    columns: tuple[Column, ...] = field(
        default=(
            Column(key="key", header="Key", type_=str),
            Column(key="value", header="Value", type_=str),
        ),
        init=False
    )
    required_keys: tuple[str, ...]


def conference_schema() -> SheetSchema:

    """Build the schema for the conference sheet.

    This includes the basic conference metadata, such as the conference name,
    location and dates.
    """

    return DictSheetSchema(
        name="Conference",
        required_keys=("conference_name", "location", "start_date", "end_date"),
    )


def program_schema() -> SheetSchema:

    """Build the schema for the program sheet.

    Note we use pandas nullable dtypes for integers, so that we can transparently
    handle missing values.
    """

    return SheetSchema(
        name="Program",
        columns=(
            Column(key="id", header="Session ID", type_="Int32"),
            Column(key="name", header="Session name", type_=str),
            Column(key="start_datetime", header="Session start", type_=str),
            Column(key="end_datetime", header="Session end", type_=str),
        )
    )


def hosts_schema() -> SheetSchema:

    """Build the schema for the hosts sheet.

    Note we use pandas nullable dtypes for integers, so that we can transparently
    handle missing values.
    """

    return SheetSchema(
        name="Hosts",
        columns=(
            Column(key="hostname", header="Hostname", type_=str),
            Column(key="screen_id", header="Screen ID", type_="Int32"),
        )
    )

def session_schema(session_id: int) -> SheetSchema:

    """Build the schema for a generic session sheet.

    Note we use pandas nullable dtypes for integers, so that we can transparently
    handle missing values.
    """

    return SheetSchema(
        name=f"{session_id}",
        columns=(
            Column(key="friendly_id", header="Friendly ID", type_="Int32"),
            Column(key="screen_id", header="Screen ID", type_="Int32"),
            Column(key="title", header="Title", type_=str),
            Column(key="first_name", header="First name", type_=str),
            Column(key="last_name", header="Last name", type_=str),
            Column(key="affiliation", header="Affiliation", type_=str),
        )
    )
