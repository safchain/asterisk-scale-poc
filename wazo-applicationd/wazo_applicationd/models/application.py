# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import datetime
import re

from pydantic import BaseModel

from wazo_appgateway_client.models.channel import Channel

from wazo_applicationd.context import Context


class Application(BaseModel):

    uuid: str

    @staticmethod
    def is_valid_uuid(uuid: str):
        regex = re.compile(
            r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}",
            re.I,
        )
        match = regex.match(uuid)
        return bool(match)


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
