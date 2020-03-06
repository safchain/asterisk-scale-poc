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

from . import helpers

logger = logging.getLogger(__name__)


@dataclass
class ChannelContext:

    channel_id: str
    context: Context


class ResourceManager:

    config: Config
    _consul: consul.aoi.Consul
    _watchers: Dict[str, Task[Any]]
    _consul_index: int
    _consul_sessions: Dict[str, str]

    def __init__(self, config: Config, discovery: Discovery) -> None:
        self.config = config

        loop = asyncio.get_event_loop()

        self._consul = consul.aio.Consul(
            host=self.config.get("consul_host"),
            port=int(self.config.get("consul_port")),
            loop=loop,
        )

        self._watchers = {}
        self._consul_index = 0
        self._consul_sessions = {}

        discovery.on_node_ok(self._on_node_ok)
        discovery.on_node_ko(self._on_node_ko)

    def _asterisk_session_name(self, context: Context) -> str:
        return "session-{}".format(context.asterisk_id)

    async def _on_node_ok(self, node: AsteriskNode) -> None:
        logger.debug("Node %s is now in OK mode", node.id)

    async def _on_node_ko(self, node: AsteriskNode) -> None:
        logger.debug("Node %s is now in KO mode", node.id)

    async def _get_or_create_session(
        self, name: str, checks: List[str] = None
    ) -> Union[int, None]:
        try:
            session = await self._consul.session.create(name=name, checks=checks)
            if not session:
                raise Exception("unable to create %s session", name)
            self._consul_sessions[name] = session

            return session
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def _kv_put(self, key: str, value: str, session: int = None) -> bool:
        logger.info("Add key %s with value %s", key, value)

        try:
            response = await self._consul.kv.put(key, value, acquire=session)
            if response is not True:
                raise Exception("unable to put key {}".format(key))
        except Exception as e:
            logger.error("Consul: %s", e)
            return False

        return True

    async def _kv_get(self, key: str) -> Union[str, None]:
        try:
            index, entry = await self._consul.kv.get(key)
            self._consul_index = int(index)
            if not entry:
                return None
            return entry.get("Value").decode()
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def _kv_get_multi(self, key: str) -> Union[List[Any], None]:
        try:
            index, entries = await self._consul.kv.get(key, recurse=True)
            self._consul_index = int(index)
            if not entries:
                return None
            return entries
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def register_master_bridge(self, context: Context, bridge_id: str) -> bool:
        session = await self._get_or_create_session(
            self._asterisk_session_name(context), [helpers.asterisk_check_id(context)]
        )
        if not session:
            return False

        return await self._kv_put(
            "bridges/{}/master".format(bridge_id), context.asterisk_id, session=session
        )

    async def register_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> bool:
        session = await self._get_or_create_session(
            self._asterisk_session_name(context), [helpers.asterisk_check_id(context)]
        )
        if not session:
            return False

        return await self._kv_put(
            "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id),
            channel_id,
            session=session,
        )

    async def _kv_delete(
        self, key, session_name: str = "", recurse: bool = False
    ) -> bool:
        logger.info("Delete key %s", key)

        try:
            response = await self._consul.kv.delete(key, recurse=recurse)
            if response is not True:
                raise Exception("unable to delete key {}".format(key))
        except Exception as e:
            logger.error("Consul: %s", e)
            return False

        return True

    async def unregister_master_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/master".format(bridge_id), recurse=True,
            )
        except Exception:
            return False

        return True

    async def unregister_slave_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id),
                recurse=True,
            )
        except Exception:
            return False

        return True

    async def unregister_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        await self._kv_delete(
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

    async def index_resource_id_context(self, context: Context, key: str) -> bool:
        session = await self._get_or_create_session(
            self._asterisk_session_name(context), [helpers.asterisk_check_id(context)]
        )
        if not session:
            return False

        return await self._kv_put(
            "resources/{}".format(key), context.asterisk_id, session=session
        )

    async def context_from_resource_id(self, key: str) -> Union[Context, None]:
        asterisk_id = await self._kv_get("resources/{}".format(key))
        if not asterisk_id:
            return None
        return Context(asterisk_id=asterisk_id)

    async def delete_resource_id_context(self, key: str) -> None:
        await self._kv_delete("resources/{}".format(key))

    def watch_key(
        self,
        watch_id: str,
        key: str,
        on_create: Callable[[str, Union[List[Any], str]], Awaitable[None]] = None,
        on_update: Callable[[str, Union[List[Any], str]], Awaitable[None]] = None,
        on_delete: Callable[[str], Awaitable[None]] = None,
    ) -> None:
        loop = asyncio.get_event_loop()
        self._watchers[watch_id] = loop.create_task(
            self._watch_key(key, on_create, on_update, on_delete)
        )

    def stop_watch_key(self, watch_id: str) -> None:
        task = self._watchers.pop(watch_id, None)
        if task:
            task.cancel()

    async def _watch_key(
        self,
        key: str,
        on_create: Callable[[str, Union[List[Any], str]], Awaitable[None]] = None,
        on_update: Callable[[str, Union[List[Any], str]], Awaitable[None]] = None,
        on_delete: Callable[[str], Awaitable[None]] = None,
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
                        key, wait="30s", index=self._consul_index
                    )
                    index = int(i)

                    if index != self._consul_index:
                        if entry:
                            if entry["CreateIndex"] == entry["ModifyIndex"]:
                                if on_create:
                                    await on_create(key, entry)
                            elif on_update:
                                await on_update(key, entry)
                        else:
                            if on_delete:
                                await on_delete(key)

                    self._consul_index = index
                except Exception as e:
                    logger.error("Consul: %s", e)
        except asyncio.CancelledError:
            pass
