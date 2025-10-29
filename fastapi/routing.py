from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .params import Depends


@dataclass
class Route:
    path: str
    method: str
    endpoint: Callable[..., Any]
    dependencies: Dict[str, Depends] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._original_path = self.path if self.path.startswith("/") else f"/{self.path}"
        self.path = self._original_path

    def set_prefix(self, prefix: str) -> None:
        base_path = self._original_path
        if prefix and not prefix.startswith("/"):
            prefix = "/" + prefix
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        self.path = f"{prefix}{base_path}" if prefix else base_path

    def match(self, path: str) -> tuple[bool, Dict[str, str]]:
        requested = [segment for segment in path.strip("/").split("/") if segment]
        defined = [segment for segment in self.path.strip("/").split("/") if segment]
        if len(requested) != len(defined):
            return False, {}
        params: Dict[str, str] = {}
        for req, defn in zip(requested, defined):
            if defn.startswith("{") and defn.endswith("}"):
                params[defn[1:-1]] = req
            elif req != defn:
                return False, {}
        return True, params


class APIRouter:
    def __init__(self) -> None:
        self.routes: List[Route] = []

    def get(self, path: str, response_model: Optional[Any] = None):
        return self._add_route(path, "GET", response_model)

    def post(self, path: str, response_model: Optional[Any] = None):
        return self._add_route(path, "POST", response_model)

    def _add_route(self, path: str, method: str, response_model: Optional[Any] = None):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            signature = inspect.signature(func)
            dependencies = {
                name: param.default
                for name, param in signature.parameters.items()
                if isinstance(param.default, Depends)
            }
            route = Route(path=path, method=method.upper(), endpoint=func, dependencies=dependencies)
            self.routes.append(route)
            return func

        return decorator
