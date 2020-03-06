# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import jwt
import asyncio
from dataclasses import dataclass


from .config import Config
from .resources import ResourceManager


@dataclass
class Context:

    asterisk_id: str

    def __eq__(self, other):
        if isinstance(other, Context):
            return self.asterisk_id == other.asterisk_id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_token(self, config: Config) -> str:
        payload = {"asterisk_id": self.asterisk_id}
        return jwt.encode(payload, config.get("jwt_secret"), algorithm="HS256").decode()

    @staticmethod
    def from_token(config: Config, token: str) -> Context:
        payload = jwt.decode(token, config.get("jwt_secret"), algorithm="HS256")
        asterisk_id = payload.get("asterisk_id", "")
        return Context(asterisk_id=asterisk_id)

    @staticmethod
    def from_resource_id(rm: ResourceManager, key: str) -> Context:
        # NOTE(safchain) should we not return the JWT to the user as a UUID
        # containing the asterisk_id and the resource ID ? This will avoid resource IDs leak
        # in the KV.
        context = asyncio.run(rm.context_from_resource_id(key))
        if context:
            return context

        return Context(asterisk_id="")
