from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .routing import Route


@dataclass
class EventHandler:
    event: str
    handler: Callable[[], Any]


class FastAPI:
    def __init__(self, title: str | None = None) -> None:
        self.title = title or "FastAPI"
        self.routes: List[Route] = []
        self._middleware: List[Any] = []
        self._events: List[EventHandler] = []

    def add_middleware(self, middleware: Any, **options: Any) -> None:
        self._middleware.append((middleware, options))

    def include_router(self, router, prefix: str = "") -> None:
        for route in router.routes:
            route.set_prefix(prefix)
            self.routes.append(route)

    def on_event(self, event: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self._events.append(EventHandler(event=event, handler=func))
            return func

        return decorator

    def trigger_event(self, event: str) -> None:
        for handler in self._events:
            if handler.event == event:
                handler.handler()

    def find_route(self, method: str, path: str) -> tuple[Route, Dict[str, str]]:
        for route in self.routes:
            if route.method != method.upper():
                continue
            matched, params = route.match(path)
            if matched:
                return route, params
        raise KeyError(f"Route not found for {method} {path}")
