# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import datetime

from pydantic import BaseModel

from wazo_appgateway_client.models.channel import Channel

from wazo_applicationd.context import Context


APP_PREFIX = "wazo-app-"


class Application(BaseModel):

    uuid: str

    @property
    def name(self):
        return Application.uuid_to_name(self.uuid)

    @staticmethod
    def name_to_uuid(name: str) -> str:
        if not name or not name.startswith(APP_PREFIX):
            return ""
        return name[len(APP_PREFIX) :]

    @staticmethod
    def uuid_to_name(uuid: str) -> str:
        return APP_PREFIX + uuid

    @staticmethod
    def is_valid(name: str) -> bool:
        return name != None and name.startswith(APP_PREFIX)


class ApplicationCall(BaseModel):

    id: str
    creation_time: datetime.date
    status: str
    caller_id_name: str
    caller_id_number: str
    muted: bool = False

    @staticmethod
    async def from_channel(context: Context, channel: Channel) -> ApplicationCall:
        return ApplicationCall(
            id=channel.id,
            creation_time=channel.creationtime,
            status=channel.state,
            caller_id_name=channel.caller.name,
            caller_id_number=channel.caller.number,
        )
