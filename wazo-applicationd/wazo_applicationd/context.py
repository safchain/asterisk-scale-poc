# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import jwt
import asyncio
import consul.aio  # type: ignore
from dataclasses import dataclass
import logging


from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class Context:

    # NOTE(safchain) shouldn't the application uuid part of the context ? it could make sense as all the resource are
    # part of an application and some of the internal things rely on application uuids (originate)
    asterisk_id: str

    def __eq__(self, other):
        if isinstance(other, Context):
            return self.asterisk_id == other.asterisk_id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def marshal(self) -> str:
        return self.asterisk_id

    @staticmethod
    def unmarshal(value: str) -> Context:
        return Context(asterisk_id=value)

    @staticmethod
    async def from_resource_id(config: Config, key: str) -> Context:
        # NOTE(safchain) should we not return the JWT to the user as a UUID
        # containing the asterisk_id and the resource ID ? This will avoid resource IDs leak
        # in the KV.
        loop = asyncio.get_event_loop()

        c = consul.aio.Consul(
            host=config.get("consul_host"),
            port=int(config.get("consul_port")),
            loop=loop,
        )

        try:
            _, entry = await c.kv.get("contexts/{}".format(key))
            if entry:
                return Context.unmarshal(entry.get("Value").decode())
        except Exception as e:
            logger.error("Context: %s", e)
        return Context(asterisk_id="")
