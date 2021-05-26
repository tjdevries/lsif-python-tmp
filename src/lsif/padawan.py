from functools import cached_property

from jedi.api.classes import Name

from lsif.types import Position
from lsif.types import Range


def _get_range(name: Name) -> Range:
    starting_pos = name.get_definition_start_position()
    assert starting_pos

    ending_pos = name.get_definition_end_position()
    assert ending_pos

    return Range(
        start=Position(line=starting_pos[0], character=starting_pos[1]),
        end=Position(line=ending_pos[0], character=ending_pos[1]),
    )


class Definition:
    _name: Name

    def __init__(self, name: Name) -> None:
        self._name = name

    @cached_property
    def range(self) -> Range:
        return _get_range(self._name)

    @cached_property
    def docstring(self) -> str:
        return self._name.docstring()


class Reference:
    _name: Name

    def __init__(self, name: Name) -> None:
        self._name = name

    @cached_property
    def range(self) -> Range:
        return _get_range(self._name)
