# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import jwt
from dataclasses import dataclass


from .config import Config

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
        asterisk_id = payload.get("asterisk_id")
        if not asterisk_id:
            raise Exception("not a valid context")

        return Context(asterisk_id)
