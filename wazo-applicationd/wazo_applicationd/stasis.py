# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging

from typing import Any

from .config import Config
from .bus import Bus
from .context import Context
from .bus import StasisEvent
from .service import Service
from .events import UserOutgoingCallCreated

from wazo_appgateway_client.models import StasisStart  # type: ignore


logger = logging.getLogger(__name__)


class Stasis:

    config: Config
    bus: Bus
    service: Service

    def __init__(self, config: Config, bus: Bus, service: Service) -> None:
        self.config = config
        self.bus = bus
        self.service = service

    def subscribe_events(self) -> None:
        self.bus.on_event("StasisStart", self.on_stasis_start)

    async def on_stasis_start(
        self, context: Context, event: StasisEvent, stasis_start: StasisStart
    ) -> None:

        # if related(cross asterisk call) push the call to the bridge
        node_uuid = await self.service.get_related_node_uuid(
            context, stasis_start.channel
        )
        if node_uuid:
            await self.service.call_answer(context, stasis_start.channel.id)

            logger.debug("Add related call to the node %s", node_uuid)
            return await self.service.insert_call_to_node(
                context, node_uuid, stasis_start.channel.id
            )

        if not stasis_start.args:
            return await self.start_user_outgoing_call(
                context, event.application_name, stasis_start
            )

        command, *command_args = stasis_start.args
        if command == "incoming":
            pass
        elif command == "originate":
            pass

    async def start_user_outgoing_call(
        self, context: Context, application_name: str, stasis_start: StasisStart,
    ) -> None:
        logger.debug("New user outgoing call %s", stasis_start.channel.id)

        application = await self.service.get_application(context, application_name)
        call = await self.service.start_user_outgoing_call(
            context, application, stasis_start.channel
        )
        event = UserOutgoingCallCreated(self.config, context, application, call)
        self.bus.publish(event)
