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
from .discovery import Discovery
from .resources import ResourceKeeper
from .events import UserOutgoingCallCreated

from wazo_appgateway_client.models.stasis_start import StasisStart  # type: ignore
from wazo_appgateway_client.models.channel_left_bridge import ChannelLeftBridge  # type: ignore
from wazo_appgateway_client.models.channel import Channel  # type: ignore
from wazo_appgateway_client.models.bridge import Bridge  # type: ignore

logger = logging.getLogger(__name__)


class Stasis:

    config: Config
    bus: Bus
    service: Service
    discovery: Discovery
    rk: ResourceKeeper

    def __init__(
        self,
        config: Config,
        bus: Bus,
        service: Service,
        discovery: Discovery,
        rk: ResourceKeeper,
    ) -> None:
        self.config = config
        self.bus = bus
        self.service = service
        self.discovery = discovery
        self.rk = rk

    def subscribe_events(self) -> None:
        self.bus.on_event("StasisStart", self.on_stasis_start)
        self.bus.on_event("ChannelLeftBridge", self.on_channel_left_bridge)

    async def on_channel_left_bridge(
        self, context: Context, event: StasisEvent, channel_left: ChannelLeftBridge
    ) -> None:
        num = len(channel_left.bridge.channels)
        if num == 1:
            last_id = channel_left.bridge.channels[0]
            type = await self.service.get_channel_var(context, last_id, "type")
            if type == "related":
                await self._hangup_related_call(context, last_id)
        elif num == 0:
            await self._cleanup_bridge(context, channel_left.bridge)

    async def on_stasis_start(
        self, context: Context, event: StasisEvent, stasis_start: StasisStart
    ) -> None:

        # if related(cross asterisk call) push the call to the bridge
        node_uuid = await self.service.get_related_node_uuid(
            context, stasis_start.channel
        )
        if node_uuid:
            return await self._answer_related_call(
                context, stasis_start.channel, node_uuid
            )

        if not stasis_start.args:
            return await self.start_user_outgoing_call(
                context, event.application_uuid, stasis_start
            )

        command, *command_args = stasis_start.args
        if command == "incoming":
            pass
        elif command == "originate":
            pass
        elif command == "related":
            pass

    async def start_user_outgoing_call(
        self, context: Context, application_uuid: str, stasis_start: StasisStart,
    ) -> None:
        logger.debug("New user outgoing call %s", stasis_start.channel.id)

        application = await self.service.get_application(context, application_uuid)
        call = await self.service.start_user_outgoing_call(
            context, application, stasis_start.channel
        )
        event = UserOutgoingCallCreated(self.config, context, application, call)
        self.bus.publish(event)

    async def _answer_related_call(
        self, context: Context, channel: Channel, node_uuid: str
    ) -> None:
        await self.service.call_answer(context, channel.id)
        await self.service.set_channel_var(context, channel, "type", "related")

        logger.debug(
            "Add related call %s to the node %s on asterisk %s",
            channel.id,
            node_uuid,
            context.asterisk_id,
        )
        return await self.service.insert_call_to_node(context, node_uuid, channel.id)

    async def _hangup_related_call(self, context: Context, channel_id: str) -> None:
        await self.service.call_hangup(context, channel_id)

    async def _cleanup_bridge(self, context: Context, bridge: Bridge) -> None:
        master_context = await self.rk.retrieve_master_node_context(bridge.id)
        if master_context and master_context.asterisk_id != context.asterisk_id:
            await self.service.delete_node(context, bridge.id)

        # await self.rk.unregister_master_node(context, bridge.id)

