# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import uvicorn  # type: ignore
from fastapi import FastAPI  # type: ignore
from starlette.requests import Request
from starlette.responses import Response

from typing import Any
from typing import Callable
from typing import Awaitable

from .config import Config
from .discovery import Discovery
from .service import Service
from .context import Context
from .consul import Consul

from .routers import application
from .routers import status

logger = logging.getLogger(__name__)


class API:

    config: Config
    discovery: Discovery
    service: Service
    consul: Consul
    _app: FastAPI

    def __init__(
        self, config: Config, discovery: Discovery, service: Service, consul: Consul
    ):
        self.config = config
        self.discovery = discovery
        self.service = service
        self.consul = consul

        self._app = FastAPI(
            title="Wazo applicationd", description="Applicationd", version="0.1.0",
        )

        self._setup_middlewares()
        self._setup_routes()

    def _setup_routes(self) -> None:
        self._app.include_router(status.router, tags=["status"])
        self._app.include_router(
            application.router, prefix="/1.0", tags=["application"]
        )

    def _setup_middlewares(self) -> None:
        self._app.middleware("http")(self._inject_deps)

    async def _inject_deps(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = Response("Internal server error", status_code=500)
        try:
            request.state.config = self.config
            request.state.discovery = self.discovery
            request.state.service = self.service
            request.state.consul = self.consul

            response = await call_next(request)
        finally:
            pass
        return response

    async def run(self) -> None:
        logger.info("Start API")

        try:
            log_level = logging.INFO
            if self.config.get("debug"):
                log_level = logging.DEBUG

            config = uvicorn.Config(
                self._app,
                host="0.0.0.0",
                port=int(self.config.get("port")),
                log_level=log_level,
            )

            server = uvicorn.Server(config)

            await server.serve()
        except asyncio.CancelledError:
            pass
