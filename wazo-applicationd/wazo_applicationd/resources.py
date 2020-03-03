# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import uuid
import asyncio
from asyncio import Queue
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

from .models.application import Application
from .models.service import AsteriskService


logger = logging.getLogger(__name__)


RESOURCE_UUID_NAMESPACE = uuid.UUID("bcfcc0df-a4a4-40fb-b760-f25eea31e95d")


def ResourceUUID(application: str, value: Union[str, None] = None) -> str:
    if value:
        return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application + "-" + value))
    return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application))


@dataclass
class ChannelContext:

    channel_id: str
    context: Context


class ResourceKeeper:

    config: Config
    _consul: consul.aoi.Consul
    _ids_to_sessions: Dict[str, str]
    _watchers: Dict[str, Awaitable[None]]
    _consul_index: int

    def __init__(self, config: Config) -> None:
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

    async def run(self) -> None:
        logger.info("Start Resource Keeper")

        loop = asyncio.get_event_loop()

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    async def _kv_put(
        self, key: str, value: str, session_name: Union[str, None] = None
    ) -> None:
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
            logger.error("Consul error: {}".format(e))

    async def _kv_get(self, key: str) -> Union[str, None]:
        try:
            index, entry = await self._consul.kv.get(key)
            self._consul_index = int(index)
            if not entry:
                return None
            return entry.get("Value").decode()
        except Exception as e:
            # TODO(safchain) need to better handling errors
            logger.debug("unable to retrieve master bridge {}".format(e))
        return None

    async def _kv_get_multi(self, key: str) -> Union[List[Any], None]:
        try:
            index, entries = await self._consul.kv.get(key, recurse=True)
            self._consul_index = int(index)
            if not entries:
                return None
            return entries
        except Exception as e:
            # TODO(safchain) need to better handling errors
            logger.debug("unable to retrieve master bridge {}".format(e))
        return None

    async def register_master_bridge(self, context: Context, bridge_id: str) -> None:
        return await self._kv_put(
            "bridges/{}/master".format(bridge_id), context.asterisk_id, bridge_id
        )

    async def register_slave_bridge_channel(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        return await self._kv_put(
            "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id),
            channel_id,
            session_name=bridge_id,
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
            logger.error("Consul error: {}".format(e))

    async def unregister_master_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/master".format(bridge_id),
                session_name=bridge_id,
                recurse=True,
            )
            return True
        except Exception:
            return False

    async def unregister_slave_bridge(self, context: Context, bridge_id: str) -> bool:
        try:
            await self._kv_delete(
                "bridges/{}/slaves/{}".format(bridge_id, context.asterisk_id),
                session_name=bridge_id,
                recurse=True,
            )
            return True
        except Exception:
            return False

    async def retrieve_master_bridge_context(
        self, context: Context, bridge_id: str
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
        self, context: Context, bridge_id: str
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
        cb: Callable[[str, str], Awaitable[None]],
        recurse=False,
    ) -> None:
        loop = asyncio.get_event_loop()
        self._watchers[watch_id] = loop.create_task(self._watch_key(key, cb))

    async def _watch_key(
        self, key: str, cb: Callable[[str, str], Awaitable[None]], recurse: bool = False
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
                        key, wait="5s", index=self._consul_index, recurse=recurse
                    )
                    index = int(i)

                    print("ooooooooooooooooooooooooooooo")
                    print(key)
                    print(index)
                    print(entry)

                    if entry and index != self._consul_index:
                        await cb(key, entry["Value"].decode())

                    self._consul_index = index
                except Exception as e:
                    # TODO(safchain) need to better handling errors
                    logger.debug("unable to retrieve master bridge {}".format(e))
        except asyncio.CancelledError:
            pass
