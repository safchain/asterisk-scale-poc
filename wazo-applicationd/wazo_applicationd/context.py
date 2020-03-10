# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
import logging


from .consul import Consul


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
    async def from_resource_id(consul: Consul, key: str) -> Context:
        # NOTE(safchain) should we not return the JWT to the user as a UUID
        # containing the asterisk_id and the resource ID ? This will avoid resource IDs leak
        # in the KV.
        try:
            _, entry = await consul.kv.get("contexts/{}".format(key))
            if entry:
                return Context.unmarshal(entry.get("Value").decode())
        except Exception as e:
            logger.error("Context: %s", e)
        return Context(asterisk_id="")
