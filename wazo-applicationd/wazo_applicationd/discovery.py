# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Queue
import consul.aio  # type: ignore
import logging

from typing import List

from .config import Config

logger = logging.getLogger(__name__)

SERVICE_ID = "applicationd"
APPLICATION_CHECK_RATE = "5s"


class Discovery:

    config: Config
    consul: consul.aoi.Consul
    queue: Queue[str]

    def __init__(self, config: Config) -> None:
        self.config = config

        loop = asyncio.get_event_loop()

        self.consul = consul.aio.Consul(
            host=self.config.consul_host,
            port=self.config.consul_port,
            loop=loop,
        )

        self.queue = asyncio.Queue()

    async def run(self) -> None:
        logger.info("Discovery start")
        await asyncio.gather(
            self.register_service(), self.register_applications(self.queue),
        )

    async def register_application(self, name: str) -> None:
        self.queue.put_nowait(name)

    async def register_applications(self, queue: Queue[str]) -> None:
        while True:
            name = await queue.get()

            try:
                logger.info(
                    "Registering application {} in Consul".format(name)
                )

                response = await self.consul.kv.put(
                    "applications/{}".format(name), name
                )
                if response is not True:
                    raise Exception(
                        "error", "registering application {}".format(name)
                    )

                service_id = "apps/{}".format(name)

                response = await self.consul.agent.service.register(
                    name,
                    service_id=service_id,
                    address=self.config.host,
                    port=self.config.port,
                )
                if response is not True:
                    raise Exception(
                        "error", "registering service {}".format(name)
                    )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Consul error: {}".format(e))

    async def register_service(self) -> None:
        while True:
            try:
                response = await self.consul.agent.service.register(
                    SERVICE_ID,
                    service_id=SERVICE_ID,
                    address=self.config.host,
                    port=self.config.port,
                )
                if response is not True:
                    raise Exception(
                        "error", "registering service %s" % SERVICE_ID
                    )

                status_url = "http://%s:%d/status" % (
                    self.config.host,
                    self.config.port,
                )
                response = await self.consul.agent.check.register(
                    SERVICE_ID,
                    consul.Check.http(status_url, "5s"),
                    service_id=SERVICE_ID,
                )
                if response is not True:
                    raise Exception(
                        "error", "registering check %s" % SERVICE_ID
                    )

                logger.info(
                    "Service check %s registered in Consul" % SERVICE_ID
                )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Consul error: %s", e)

            await asyncio.sleep(5)
