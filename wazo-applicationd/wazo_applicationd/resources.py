# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import uuid
import asyncio
from asyncio import Queue
import consul.aio  # type: ignore
import logging

from typing import Union
from typing import Dict

from .config import Config
from .context import Context

from .models.application import Application
from .models.node import ApplicationNode
from .models.service import AsteriskService


logger = logging.getLogger(__name__)


RESOURCE_UUID_NAMESPACE = uuid.UUID("bcfcc0df-a4a4-40fb-b760-f25eea31e95d")


def ResourceUUID(application: str, value: Union[str, None] = None) -> str:
    if value:
        return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application + "-" + value))
    return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application))


class ResourceKeeper:

    config: Config
    _consul: consul.aoi.Consul
    _ids_to_sessions: Dict[str, str]

    def __init__(self, config: Config) -> None:
        self.config = config

        loop = asyncio.get_event_loop()

        self._consul = consul.aio.Consul(
            host=self.config.get("consul_host"),
            port=self.config.get("consul_port"),
            loop=loop,
        )

        self._ids_to_sessions = {}

    async def register_master_node(
        self, context: Context, node: ApplicationNode
    ) -> None:
        logger.info("Add a session for node {} in Consul".format(node.uuid))
        try:
            session = await self._consul.session.create(name=node.uuid)
            self._ids_to_sessions[node.uuid] = session

            response = await self._consul.kv.put(
                "bridges/{}/master".format(node.uuid),
                context.asterisk_id,
                acquire=session,
            )
            if response is not True:
                raise Exception("error")
        except Exception as e:
            logger.error("Consul error: {}".format(e))

    async def unregister_master_node(self, context: Context, node_uuid: str) -> None:
        session = self._ids_to_sessions[node_uuid]
        try:
            response = await self._consul.kv.delete(
                "bridges/{}".format(node_uuid), context.asterisk_id, acquire=session,
            )
            if response is not True:
                raise Exception("error")
            self._ids_to_sessions.pop(node_uuid)
        except Exception as e:
            logger.error("Consul error: {}".format(e))

    async def retrieve_master_node_context(
        self, node_uuid: str
    ) -> Union[Context, None]:
        try:
            _, entry = await self._consul.kv.get("bridges/{}/master".format(node_uuid))
            return Context(entry["Value"].decode())
        except Exception as e:
            # TODO(safchain) need to better handling errors
            logger.debug("unable to retrieve master node {}".format(e))

        return None
