# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Task
import logging

from typing import Any
from typing import List
from typing import Union
from typing import Dict
from typing import Callable
from typing import Awaitable

from .config import Config
from .consul import Consul


logger = logging.getLogger(__name__)


class LeaderManager:

    config: Config
    consul: Consul
    _elections: Dict[str, Task[Any]]

    def __init__(self, config: Config, consul: Consul) -> None:
        self.config = config
        self.consul = consul

        self._elections = {}

    async def _wait_for_key_update(self, key: str, wait: int) -> None:
        index, _ = await self.consul.kv.get(key)
        await self.consul.kv.get(key, wait="{}s".format(wait), index=str(index))

    async def start_election(
        self,
        key: str,
        on_master: Callable[[str], Awaitable[None]] = None,
        on_slave: Callable[[str], Awaitable[None]] = None,
        checks: List[str] = None,
    ) -> None:
        loop = asyncio.get_event_loop()
        self._elections[key] = loop.create_task(
            self._start_election(key, on_master, on_slave, checks=checks)
        )

    async def stop_election(self, key: str) -> None:
        task = self._elections.pop(key, None)
        if task:
            task.cancel()

    async def _start_election(
        self,
        key: str,
        on_master: Callable[[str], Awaitable[None]] = None,
        on_slave: Callable[[str], Awaitable[None]] = None,
        checks: List[str] = None,
    ) -> None:
        is_master: bool = False
        is_first_pass: bool = True
        session: str = ""
        ttl: int = 20

        try:
            while True:
                logger.debug(
                    "Master election for %s, currently in %s mode",
                    key,
                    "master" if is_master else "slave",
                )

                is_success: bool = False
                try:
                    if not session:
                        session = await self.consul.session.create(
                            name=key, behavior="delete", checks=checks, ttl=ttl
                        )
                    else:
                        res = await self.consul.session.renew(session)
                        session = res.get('ID')

                    is_success = await self.consul.kv.put(key, key, acquire=session)
                except Exception as e:
                    session = ""
                    await asyncio.sleep(1)
                    continue

                if is_success:
                    if not is_master:
                        is_master = True

                        logger.debug("Became master for %s", key)

                        if on_master:
                            await on_master(key)
                else:
                    if is_master or is_first_pass:
                        is_master = False

                        logger.debug("Became slave for %s", key)

                        if on_slave:
                            await on_slave(key)

                is_first_pass = False

                await self._wait_for_key_update(key, int(ttl / 2))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error during election %s", e)

