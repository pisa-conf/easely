# Copyright (C) 2024--2026 the easely team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pytest

from easely import img


def test_rectangle(width: int = 100, height: int = 200) -> None:
    """Unit tests for the Rectangle class.
    """
    # Test that invalid Rectangle parameters.
    with pytest.raises(TypeError):
        img.Rectangle(0., 0., width, height)
    with pytest.raises(ValueError):
        img.Rectangle(0, 0, -1, height)

    # Test valid Rectangle object with different offsets, exercising the main
    # interfaces.
    for (x0, y0) in ((0, 0), (10, 20)):
        rectangle = img.Rectangle(x0, y0, width, height)
        assert rectangle.x0 == x0
        assert rectangle.y0 == y0
        assert rectangle.width == width
        assert rectangle.height == height
        assert rectangle.area() == width * height
        bbox = (x0, y0, x0 + width, y0 + height)
        assert rectangle.bounding_box() == bbox
        assert rectangle == img.Rectangle.from_bounding_box(bbox)
        assert rectangle == rectangle.copy()
        assert rectangle.is_square() is False

    # Check the largest_centered_square() method.
    assert rectangle.largest_centered_square(100, 200) == img.Rectangle(0, 50, 100, 100)

    # Check the equal_area_square() method.
    assert img.Rectangle(10, 10, 81, 100).equal_area_square() == img.Rectangle(6, 15, 90, 90)
