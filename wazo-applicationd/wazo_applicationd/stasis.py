# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging

from typing import Any

from .bus import Bus
from .context import Context
from .bus import StasisEvent
from .service import Service

from openapi_client.models import StasisStart  # type: ignore


logger = logging.getLogger(__name__)


class Stasis:

    bus: Bus
    service: Service

    def __init__(self, bus: Bus, service: Service) -> None:
        self.bus = bus
        self.service = service

    def subscribe_events(self) -> None:
        self.bus.on_event("StasisStart", self.on_stasis_start)

    async def on_stasis_start(
        self, context: Context, event: StasisEvent, stasis_start: StasisStart
    ) -> None:
        if not stasis_start.args:
            return await self.start_user_outgoing(
                context, event.application_name, stasis_start
            )

        command, *command_args = stasis_start.args
        if command == "incoming":
            pass
        elif command == "originate":
            pass

        """
        application_uuid = AppNameHelper.to_uuid(event.get('application'))
        if not application_uuid:
            return

        if not event['args']:
            return self._stasis_start_user_outgoing(application_uuid, event_objects, event)

        command, *command_args = event['args']
        if command == 'incoming':
            self._stasis_start_incoming(application_uuid, event_objects, event)
        elif command == 'originate':
            node_uuid = command_args[0] if command_args else None
            self._stasis_start_originate(application_uuid, node_uuid, event_objects, event)
        """

    async def start_user_outgoing(
        self, context: Context, application_name: str, stasis_start: StasisStart,
    ) -> None:
        logger.debug("New user outgoing call %s", stasis_start.channel.id)

        application = await self.service.get_application(context, application_name)
        await self.service.start_user_outgoing_call(
            context, application, stasis_start.channel
        )
