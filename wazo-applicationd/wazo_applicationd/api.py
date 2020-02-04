# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import consul.aio  # type: ignore
import uvicorn  # type: ignore
from fastapi import FastAPI  # type: ignore

from typing import Any

from .config import Config
from .discovery import Discovery

logger = logging.getLogger(__name__)


class API:

    config: Config
    discovery: Discovery
    fastapi: FastAPI

    def __init__(self, config: Config, discovery: Discovery):
        self.config = config
        self.discovery = discovery

        self.fastapi = FastAPI()

    async def run(self) -> None:
        logger.info("start API")

        try:
            self.fastapi.get("/status")(self.status)
            self.fastapi.post("/applications/{name}")(self.applications_post)

            config = uvicorn.Config(
                self.fastapi, host="0.0.0.0", port=self.config.port
            )

            server = uvicorn.Server(config)

            await server.serve()
        except asyncio.CancelledError:
            pass

    async def status(self) -> Any:
        return {"state": "ok"}

    async def applications_post(self, name: str) -> Any:
        print(name)

        await self.discovery.register_application(name)
