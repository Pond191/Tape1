from __future__ import annotations

import asyncio
import inspect
import json
from io import BytesIO
from typing import Any, Dict, Optional

from ..application import FastAPI
from ..background import BackgroundTasks
from ..exceptions import HTTPException
from ..params import Depends, File, Form
from ..requests import UploadFile
from ..responses import FileResponse


class Response:
    def __init__(self, status_code: int, data: Any) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> Any:
        if hasattr(self._data, "dict"):
            return self._data.dict()
        if isinstance(self._data, (dict, list)):
            return self._data
        if isinstance(self._data, str):
            try:
                return json.loads(self._data)
            except json.JSONDecodeError:
                return self._data
        if isinstance(self._data, bytes):
            try:
                return json.loads(self._data.decode("utf-8"))
            except Exception:
                return self._data
        return self._data

    @property
    def content(self) -> bytes:
        if isinstance(self._data, bytes):
            return self._data
        if isinstance(self._data, str):
            return self._data.encode("utf-8")
        if hasattr(self._data, "read"):
            return self._data.read()
        if hasattr(self._data, "dict"):
            return json.dumps(self._data.dict(), ensure_ascii=False).encode("utf-8")
        return json.dumps(self.json(), ensure_ascii=False).encode("utf-8")


class TestClient:
    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.app.trigger_event("startup")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Response:
        return self._request("GET", path, data=params or {})

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Response:
        return self._request("POST", path, data=data or {}, files=files or {})

    def _request(
        self,
        method: str,
        path: str,
        data: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
    ) -> Response:
        files = files or {}
        clean_path = path.split("?")[0]
        try:
            route, path_params = self.app.find_route(method, clean_path)
        except KeyError:
            return Response(404, {"detail": "Not Found"})

        signature = inspect.signature(route.endpoint)
        kwargs: Dict[str, Any] = {}
        cleanups = []
        background = None

        for name, param in signature.parameters.items():
            if name in path_params:
                kwargs[name] = path_params[name]
                continue

            default = param.default
            if isinstance(default, Depends):
                dependency = default.dependency
                value = dependency()
                if inspect.isgenerator(value):
                    gen = value
                    try:
                        value = next(gen)
                    except StopIteration:
                        value = None
                    else:
                        cleanups.append(lambda *_args, _gen=gen: _gen.close())
                if hasattr(value, "__enter__") and hasattr(value, "__exit__"):
                    ctx = value
                    value = ctx.__enter__()
                    cleanups.append(ctx.__exit__)
                kwargs[name] = value
                continue

            if (
                param.annotation is BackgroundTasks
                or getattr(param.annotation, "__name__", "") == "BackgroundTasks"
                or isinstance(default, BackgroundTasks)
                or name == "background_tasks"
            ):
                background = BackgroundTasks()
                kwargs[name] = background
                continue

            if isinstance(default, File):
                file_info = files.get(name)
                if not file_info:
                    raise HTTPException(status_code=400, detail=f"Missing file {name}")
                if isinstance(file_info, (list, tuple)):
                    filename = file_info[0]
                    fileobj = file_info[1] if len(file_info) > 1 else BytesIO()
                else:
                    filename = getattr(file_info, "name", "upload.bin")
                    fileobj = file_info
                upload = UploadFile(filename=filename, file=fileobj)
                kwargs[name] = upload
                continue

            if isinstance(default, Form):
                kwargs[name] = data.get(name, default.default)
                continue

            if name in data:
                kwargs[name] = data[name]
                continue

            if param.default is inspect._empty:
                kwargs[name] = None

        try:
            result = route.endpoint(**kwargs)
            if inspect.iscoroutine(result):
                result = asyncio.run(result)
        except HTTPException as exc:
            for cleanup in cleanups:
                cleanup(None, None, None)
            if background:
                background.tasks.clear()
            return Response(exc.status_code, {"detail": exc.detail})

        for cleanup in cleanups:
            cleanup(None, None, None)

        if background:
            background.run()

        if isinstance(result, FileResponse):
            return Response(200, result.read())

        if hasattr(result, "dict"):
            return Response(200, result)

        return Response(200, result)
