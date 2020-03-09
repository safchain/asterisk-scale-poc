# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Task
import consul.aio  # type: ignore
import logging

from typing import Any
from typing import Union
from typing import List
from typing import Dict
from typing import Callable
from typing import Awaitable

from .config import Config

logger = logging.getLogger(__name__)


class Consul:

    config: Config
    _consul: consul.aoi.Consul
    _watchers: Dict[str, Task[Any]]
    _consul_sessions: Dict[str, str]

    def __init__(self, config: Config) -> None:
        self.config = config

        loop = asyncio.get_event_loop()

        self._consul = consul.aio.Consul(
            host=self.config.get("consul_host"),
            port=int(self.config.get("consul_port")),
            loop=loop,
        )

        self._watchers = {}
        self._consul_sessions = {}

    @property
    def kv(self) -> Any:
        return self._consul.kv

    @property
    def session(self) -> Any:
        return self._consul.session

    @property
    def agent(self) -> Any:
        return self._consul.agent

    @property
    def health(self) -> Any:
        return self._consul.health

    async def get_or_create_session(
        self, name: str, checks: List[str] = None
    ) -> Union[str, None]:
        session = self._consul_sessions.get(name)
        if session:
            return session

        try:
            session = await self._consul.session.create(name=name, checks=checks)
            if not session:
                raise Exception("unable to create %s session", name)
            self._consul_sessions[name] = session

            return session
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def release_session(self, name) -> None:
        session = self._consul_sessions.get(name)
        if not session:
            return None

        try:
            await self._consul.session.destroy(session)
        except Exception as e:
            logger.error("Consul: %s", e)

    async def kv_put(self, key: str, value: str, session: str = None) -> bool:
        logger.info("Add key %s with value %s", key, value)

        try:
            response = await self._consul.kv.put(key, value, acquire=session)
            if response is not True:
                raise Exception("unable to put key {}".format(key))
        except Exception as e:
            logger.error("Consul: %s", e)
            return False

        return True

    async def kv_get(self, key: str) -> Union[str, None]:
        try:
            _, entry = await self._consul.kv.get(key)
            if not entry:
                return None
            return entry.get("Value").decode()
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def kv_get_multi(self, key: str) -> Union[List[Any], None]:
        try:
            _, entries = await self._consul.kv.get(key, recurse=True)
            if not entries:
                return None
            return entries
        except Exception as e:
            logger.error("Consul: %s", e)
        return None

    async def kv_delete(
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
            i, _ = await self._consul.kv.get(key)
            prev_index = int(i)

            while True:
                try:
                    logger.debug(
                        "Check changes for on key %s with index %d", key, prev_index,
                    )

                    i, entry = await self._consul.kv.get(
                        key, wait="30s", index=prev_index
                    )
                    index = int(i)

                    if index != prev_index:
                        if entry:
                            if entry["CreateIndex"] == entry["ModifyIndex"]:
                                if on_create:
                                    await on_create(key, entry)
                            elif on_update:
                                await on_update(key, entry)
                        else:
                            if on_delete:
                                await on_delete(key)

                    prev_index = index
                except Exception as e:
                    logger.error("Consul: %s", e)
        except asyncio.CancelledError:
            pass
