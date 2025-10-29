from __future__ import annotations

from typing import Any, Callable, List


class BackgroundTasks:
    def __init__(self) -> None:
        self.tasks: List[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []

    def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.tasks.append((func, args, kwargs))

    def run(self) -> None:
        for func, args, kwargs in self.tasks:
            func(*args, **kwargs)
