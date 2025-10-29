from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Depends:
    dependency: Callable[..., Any]


@dataclass
class File:
    default: Any


@dataclass
class Form:
    default: Any
