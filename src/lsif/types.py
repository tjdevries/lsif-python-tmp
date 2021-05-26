# from typing import Callable
from dataclasses import dataclass
from typing import Any
from typing import Protocol


class Writer(Protocol):
    def write(self, s: str) -> Any:
        pass


@dataclass(frozen=True)
class Position:
    line: int
    character: int


@dataclass(frozen=True)
class Range:
    start: Position
    end: Position
