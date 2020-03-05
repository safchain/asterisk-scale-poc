# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Task
import consul.aio  # type: ignore
import logging
from dataclasses import dataclass
import os

from typing import Union
from typing import Dict
from typing import Callable
from typing import Awaitable
from typing import List
from typing import Any

from .config import Config
from .context import Context
from .discovery import Discovery

from .models.application import Application
from .models.service import AsteriskNode


logger = logging.getLogger(__name__)


@dataclass
class ChannelContext:

    channel_id: str
    context: Context


class ResourceManager:

    config: Config
    _consul: consul.aoi.Consul
    _ids_to_sessions: Dict[str, str]
    _watchers: Dict[str, Task[Any]]
    _consul_index: int

    def __init__(self, config: Config, discovery: Discovery) -> None:
        self.config = config

        loop = asyncio.get_event_loop()

        self._consul = consul.aio.Consul(
            host=self.config.get("consul_host"),
            port=self.config.get("consul_port"),
            loop=loop,
        )

        self._ids_to_sessions = {}
        self._watchers = {}
        self._consul_index = 0

        discovery.on_node_ok(self._on_node_ok)
        discovery.on_node_ko(self._on_node_ko)

    async def _on_node_ok(self, node: AsteriskNode) -> None:
        print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOO" + node.id)

    async def _on_node_ko(self, node: AsteriskNode) -> None:
        print("KKKKKKKKKKKKKKKKKKKKKKKKKKKKKK" + node.id)

    async def _kv_put(self, key: str, value: str, session_name: str = None) -> None:
        logger.info("Add key %s with value %s", key, value)

        try:
            session: str = ""
            if session_name:
                session = await self._consul.session.create(name=session_name)
                self._ids_to_sessions[session_name] = session

            response = await self._consul.kv.put(key, value, acquire=session)
            if response is not True:
                raise Exception("error")
        except Exception as e:
            logger.error("Consul error %s", e)

    async def _kv_get(self, key: str) -> Union[str, None]:
        try:
            index, entry = await self._consul.kv.get(key)
            self._consul_index = int(index)
            if not entry:
                return None
            return entry.get("Value").decode()
        except Exception as e:
            logger.error("Consul error %s", e)
        return None

    async def _kv_get_multi(self, key: str) -> Union[List[Any], None]:
        try:
            index, entries = await self._consul.kv.get(key, recurse=True)
            self._consul_index = int(index)
            if not entries:
                return None
            return entries
        except Exception as e:
            logger.error("Consul error %s", e)
        return None

    async def register_master_bridge(self, context: Context, bridge_id: str) -> None:
        return await self._kv_put(
            "bridges/{}/master".format(bridge_id), context.asterisk_id
        )

    async def register_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        return await self._kv_put(
            "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id), channel_id
        )

    async def _kv_delete(
        self, key, session_name: str = "", recurse: bool = False
    ) -> None:
        logger.info("Delete key %s", key)

        self._ids_to_sessions.pop(session_name, None)
        try:
            response = await self._consul.kv.delete(key, recurse=recurse)
            if response is not True:
                raise Exception("error")
        except Exception as e:
            logger.error("Consul error %s", e)

    async def unregister_master_bridge(self, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/master".format(bridge_id), recurse=True,
            )
            return True
        except Exception:
            return False

    async def unregister_slave_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id),
                recurse=True,
            )
            return True
        except Exception:
            return False

    async def unregister_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        return await self._kv_delete(
            "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id)
        )

    async def retrieve_master_bridge_context(
        self, bridge_id: str
    ) -> Union[Context, None]:
        value = await self._kv_get("bridges/{}/master".format(bridge_id))
        if value:
            return Context(asterisk_id=value)
        return None

    async def retrieve_slave_bridge_channel(
        self, context: Context, bridge_id: str
    ) -> Union[str, None]:
        return await self._kv_get(
            "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id)
        )

    async def retrieve_slave_bridge_channel_contexts(
        self, bridge_id: str
    ) -> List[ChannelContext]:
        entries = await self._kv_get_multi("bridges/{}/slaves/".format(bridge_id))
        if not entries:
            return []

        ch_contexts: List[ChannelContext] = []
        for entry in entries:
            channel_id = entry.get("Value").decode()
            asterisk_id = os.path.basename(entry.get("Key"))
            ch_contexts.append(
                ChannelContext(
                    channel_id=channel_id, context=Context(asterisk_id=asterisk_id)
                )
            )

        return ch_contexts

    def watch_key(
        self,
        watch_id: str,
        key: str,
        cb: Callable[[str, Union[List[Any], str]], Awaitable[None]],
        recurse=False,
    ) -> None:
        loop = asyncio.get_event_loop()
        self._watchers[watch_id] = loop.create_task(self._watch_key(key, cb))

    def stop_watch_key(self, watch_id: str) -> None:
        task = self._watchers.get(watch_id)
        if task:
            task.cancel()

    async def _watch_key(
        self,
        key: str,
        cb: Callable[[str, Union[List[Any], str]], Awaitable[None]],
        recurse: bool = False,
    ) -> None:
        try:
            while True:
                try:
                    logger.debug(
                        "Check changes for on key %s with index %d",
                        key,
                        self._consul_index,
                    )

                    i, entry = await self._consul.kv.get(
                        key, wait="30s", index=self._consul_index, recurse=recurse
                    )
                    index = int(i)

                    if entry and index != self._consul_index:
                        if recurse:
                            await cb(key, entry["Value"].decode())
                        else:
                            await cb(key, entry)

                    self._consul_index = index
                except Exception as e:
                    logger.error("Consul error %s", e)
        except asyncio.CancelledError:
            pass
