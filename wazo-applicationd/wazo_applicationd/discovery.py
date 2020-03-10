# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Task
import logging
import consul  # type: ignore

from typing import Any
from typing import List
from typing import Union
from typing import Dict
from typing import Awaitable
from typing import Callable

from .config import Config
from .context import Context
from .consul import Consul

from .models.application import Application
from .models.service import AsteriskNode, Status

from . import helpers

logger = logging.getLogger(__name__)

SERVICE_ID = "applicationd"


class Discovery:

    config: Config
    consul: Consul
    _node_ok_cbs: List[Callable[[AsteriskNode], Awaitable[None]]]
    _node_ko_cbs: List[Callable[[AsteriskNode], Awaitable[None]]]

    def __init__(self, config: Config, consul: Consul) -> None:
        self.config = config
        self.consul = consul

        self._ast_nodes_watcher_task = None
        self._node_ok_cbs = []
        self._node_ko_cbs = []

    async def run(self) -> None:
        logger.info("Start Discovery")
        await asyncio.gather(self._register_service(), self._watch_ast_nodes())

    async def register_application(self, name: str) -> Application:
        application = Application(uuid=helpers.resource_uuid(name))
        application_uuid = application.uuid

        logger.info("Registering application {} in Consul".format(name))
        try:
            response = await self.consul.kv.put(
                "applications/{}".format(application_uuid), application_uuid
            )
            if response is not True:
                raise Exception("registering app {}".format(name))
        except Exception as e:
            logger.error("Consul: %s", e)

        return application

    def http_service_check_id(self) -> str:
        return "http-status-{}".format(self.config.get("uuid"))

    async def _register_service(self) -> None:
        uuid = self.config.get("uuid")
        while True:
            try:
                response = await self.consul.agent.service.register(
                    SERVICE_ID,
                    service_id=uuid,
                    address=self.config.get("host"),
                    port=int(self.config.get("port")),
                )
                if response is not True:
                    raise Exception("registering service node {}".format(uuid))

                response = await self.consul.agent.check.register(
                    self.http_service_check_id(),
                    consul.Check.http(self.config.get("healthcheck_url"), "15s"),
                    service_id=uuid,
                )
                if response is not True:
                    raise Exception("registering node check {}".format(uuid))

                logger.info("Node %s registered in Consul", uuid)

                return None
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Consul: %s", e)

            await asyncio.sleep(5)

    def _is_node_checks_passing(self, node: Dict[str, Any]) -> bool:
        for check in node.get("Checks", []):
            if check.get("Status") != "passing":
                return False
        return True

    def _to_asterisk_node(self, node: Dict[str, Any]) -> Union[AsteriskNode, None]:
        service = node.get("Service", {})
        meta = service.get("Meta", {})

        id = meta.get("eid")
        address = service.get("Address")
        port = service.get("Port")

        if not id or not address or not port:
            return None

        status = Status.OK if self._is_node_checks_passing(node) else Status.KO

        return AsteriskNode(id=id, address=address, port=int(port), status=status)

    async def retrieve_asterisk_nodes(
        self, filter_status: str = None
    ) -> Dict[str, AsteriskNode]:
        ast_nodes: Dict[str, AsteriskNode] = {}

        try:
            _, nodes = await self.consul.health.service("asterisk")
        except Exception as e:
            logger.error("Consul: %s", e)
            return ast_nodes

        for node in nodes:
            ast_node = self._to_asterisk_node(node)
            if not ast_node:
                logger.error("Asterisk node definition incomplete")
                continue

            if not filter_status or ast_node.status == filter_status:
                ast_nodes[ast_node.id] = ast_node

        return ast_nodes

    async def _watch_ast_nodes(self) -> None:
        logging.info("Start watching nodes")
        try:
            ast_nodes = await self.retrieve_asterisk_nodes()
            for id_, ast_node_ in ast_nodes.items():
                if ast_node_.status == Status.OK:
                    for cb in self._node_ok_cbs:
                        await cb(ast_node_)
                else:
                    for cb in self._node_ko_cbs:
                        await cb(ast_node_)

            i, _ = await self.consul.health.service("asterisk")
            prev_index = int(i)

            while True:
                try:
                    logger.debug(
                        "Check changes on asterisk nodes index %d", prev_index,
                    )

                    i, nodes = await self.consul.health.service(
                        "asterisk", wait="30s", index=prev_index
                    )
                    index = int(i)

                    if nodes and index != prev_index:
                        for node in nodes:
                            ast_node = self._to_asterisk_node(node)
                            if not ast_node:
                                logger.error("Asterisk node definition incomplete")
                                continue

                            if ast_node.status == Status.OK:
                                if ast_node.status != ast_nodes.get(
                                    ast_node.id, Status.KO
                                ):
                                    for cb in self._node_ok_cbs:
                                        await cb(ast_node)
                            else:
                                if ast_node.status != ast_nodes.get(
                                    ast_node.id, Status.OK
                                ):
                                    for cb in self._node_ko_cbs:
                                        await cb(ast_node)

                            ast_nodes[ast_node.id] = ast_node

                    prev_index = index
                except Exception as e:
                    logger.error("unable to get node states %s", e)
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error while watching asterisk nodes %s", e)

    def on_node_ok(self, cb: Callable[[AsteriskNode], Awaitable[None]]) -> None:
        self._node_ok_cbs.append(cb)

    def on_node_ko(self, cb: Callable[[AsteriskNode], Awaitable[None]]) -> None:
        self._node_ko_cbs.append(cb)
