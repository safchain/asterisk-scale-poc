# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Task
import logging
from dataclasses import dataclass
import os
from datetime import datetime

from typing import Union
from typing import Dict
from typing import List
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Tuple

from .config import Config
from .context import Context
from .discovery import Discovery
from .consul import Consul

from .models.application import Application
from . import helpers

logger = logging.getLogger(__name__)


SESSION_RESOURCE_TIMEOUT = 3600  # will create a new session every N seconds
SESSION_RESOURCE_TTL = (
    3600 * 6
)  # each session will be released everty N seconds, ex a channel attached to a session will be released too


@dataclass
class ChannelContext:

    channel_id: str
    context: Context


class ResourceManager:

    config: Config
    consul: Consul
    _session_resource: str
    _session_resource_time: datetime

    def __init__(self, config: Config, consul: Consul, discovery: Discovery) -> None:
        self.config = config
        self.consul = consul

        self._session_resource = ""

    def _asterisk_session_name(self, context: Context) -> str:
        return "session-{}".format(context.asterisk_id)

    async def register_master_bridge(self, context: Context, bridge_id: str) -> bool:
        session = await self.consul.get_or_create_session(
            self._asterisk_session_name(context), [helpers.asterisk_check_id(context)]
        )
        if not session:
            return False

        is_success = await self.consul.kv_put(
            "bridges/masters/{}".format(bridge_id), context.asterisk_id, session=session
        )
        if not is_success:
            return False

        return True

    async def register_slave_bridge_channel(
        self, context: Context, application_uuid: str, bridge_id: str, channel_id: str
    ) -> bool:
        session = await self.consul.get_or_create_session(
            self._asterisk_session_name(context), [helpers.asterisk_check_id(context)]
        )
        if not session:
            return False

        return await self.consul.kv_put(
            "bridges/slaves/{}/{}".format(bridge_id, context.asterisk_id),
            "{}/{}".format(application_uuid, channel_id),
            session=session,
        )

    async def unregister_master_bridge(self, bridge_id: str) -> bool:
        try:
            await self.consul.kv_delete(
                "bridges/masters/{}".format(bridge_id), recurse=True,
            )
        except Exception:
            return False

        return True

    async def unregister_slave_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self.consul.kv_delete(
                "bridges/slaves/{}/{}".format(bridge_id, context.asterisk_id),
                recurse=True,
            )
        except Exception:
            return False

        return True

    async def unregister_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        await self.consul.kv_delete(
            "bridges/slaves/{}/{}".format(bridge_id, context.asterisk_id)
        )

    async def retrieve_master_bridge_context(
        self, bridge_id: str
    ) -> Union[Context, None]:
        value = await self.consul.kv_get("bridges/masters/{}".format(bridge_id))
        if value:
            return Context(asterisk_id=value)
        return None

    async def retrieve_slave_bridge_channel(
        self, context: Context, bridge_id: str
    ) -> Tuple[str, str]:
        value = await self.consul.kv_get(
            "bridges/slaves/{}/{}".format(bridge_id, context.asterisk_id)
        )
        if not value:
            return ("", "")

        application_uuid, channel = value.split("/")
        return (application_uuid, channel)

    async def retrieve_slave_bridge_channel_contexts(
        self, bridge_id: str
    ) -> List[ChannelContext]:
        entries = await self.consul.kv_get_multi("bridges/slaves/{}".format(bridge_id))
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

    async def index_resource_id_context(self, context: Context, id: str) -> bool:
        if (
            not self._session_resource
            or (datetime.now() - self._session_resource_time).total_seconds()
            > SESSION_RESOURCE_TIMEOUT
        ):
            name = self._asterisk_session_name(context)

            try:
                session = await self.consul.session.create(
                    name=name,
                    checks=[helpers.asterisk_check_id(context)],
                    behavior="delete",
                    ttl=SESSION_RESOURCE_TIMEOUT * 2,
                )
                if not session:
                    raise Exception("unable to create {} session".format(name))
                self._session_resource = session
                self._session_resource_time = datetime.now()
            except:
                raise Exception("unable to create {} session".format(name))

        if not self._session_resource:
            raise Exception("no session available")

        return await self.consul.kv_put(
            "contexts/{}".format(id),
            context.marshal(),
            session=self._session_resource,
        )

    async def delete_resource_id_context(self, id: str) -> None:
        await self.consul.kv_delete("contexts/{}".format(id))

    def watch_master_bridges(
        self,
        id: str,
        on_create: Callable[[str, str], Awaitable[None]] = None,
        on_update: Callable[[str, str], Awaitable[None]] = None,
        on_delete: Callable[[str], Awaitable[None]] = None,
    ) -> None:
        watcher = BridgeWatcher(
            on_create=on_create, on_update=on_update, on_delete=on_delete
        )

        self.consul.watch_key(
            "master-bridges-watcher-{}".format(id),
            "bridges/masters/",
            on_create=watcher.on_create,
            on_update=watcher.on_update,
            on_delete=watcher.on_delete,
            recurse=True,
        )

    def stop_watch_master_bridges(self, id: str) -> None:
        self.consul.stop_watch_key("master-bridges-watcher-{}".format(id))


class BridgeWatcher:

    _on_create: Union[Callable[[str, str], Awaitable[None]], None]
    _on_update: Union[Callable[[str, str], Awaitable[None]], None]
    _on_delete: Union[Callable[[str], Awaitable[None]], None]

    def __init__(
        self,
        on_create: Callable[[str, str], Awaitable[None]] = None,
        on_update: Callable[[str, str], Awaitable[None]] = None,
        on_delete: Callable[[str], Awaitable[None]] = None,
    ):
        self._on_create = on_create
        self._on_update = on_update
        self._on_delete = on_delete

    def _bridge_from_path(self, key: str) -> str:
        return os.path.basename(key)

    async def on_create(self, key: str, value: str) -> None:
        if self._on_create:
            await self._on_create(self._bridge_from_path(key), value)

    async def on_update(self, key: str, value: str) -> None:
        if self._on_update:
            await self._on_update(self._bridge_from_path(key), value)

    async def on_delete(self, key: str) -> None:
        if self._on_delete:
            await self._on_delete(self._bridge_from_path(key))
