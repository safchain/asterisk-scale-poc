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
from .exceptions import NoSuchChannelException

from wazo_appgateway_client.models.stasis_start import StasisStart  # type: ignore
from wazo_appgateway_client.models.channel_left_bridge import ChannelLeftBridge  # type: ignore
from wazo_appgateway_client.models.channel import Channel  # type: ignore
from wazo_appgateway_client.models.bridge import Bridge  # type: ignore
from wazo_appgateway_client.models.channel_entered_bridge import ChannelEnteredBridge  # type: ignore
from wazo_appgateway_client.models.bridge_destroyed import BridgeDestroyed  # type: ignore

from .models.application import ApplicationCall

logger = logging.getLogger(__name__)


RELATED_BRIDGE_ID_HEADER = "X-Related-Bridge-ID"


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
        self.bus.on_event("BridgeDestroyed", self.on_bridge_destroyed)
        self.bus.on_event("ChannelEnteredBridge", self.on_channel_entered_bridge)

    async def on_bridge_destroyed(
        self, context: Context, event: StasisEvent, bridge_destroyed: BridgeDestroyed
    ) -> None:
        master_context = await self.rk.retrieve_master_bridge_context(
            context, bridge_destroyed.bridge.id
        )
        if master_context and master_context == context:
            await self._promote_new_master_bridge(context, bridge_destroyed.bridge.id)
        else:
            await self.rk.unregister_slave_bridge(context, bridge_destroyed.bridge.id)

    async def _promote_new_master_bridge(
        self, context: Context, bridge_id: str
    ) -> None:
        logger.info("Promote a new master bridge")

        # hangup all related channels
        ch_contexts = await self.rk.retrieve_slave_bridge_channel_contexts(
            context, bridge_id
        )
        print("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
        print(ch_contexts)

        if not ch_contexts:
            # no more slave available then delete the master
            self.rk.unregister_master_bridge(context, bridge_id)

        # be sure that all the channel to previous master are terminted
        for ch_context in ch_contexts:
            try:
                await self.service.channel_hangup(
                    ch_context.context, ch_context.channel_id
                )
            except NoSuchChannelException:
                pass

        # promote a slave as new master

    async def _eheh(self, key: str, value: str) -> None:
        print("ZZZZZZZZZZZZZZZZZZZZZZ")
        print(key)
        print(value)

    async def on_channel_entered_bridge(
        self,
        context: Context,
        event: StasisEvent,
        channel_entered: ChannelEnteredBridge,
    ) -> None:
        bridge_id = channel_entered.bridge.id

        # register this asterisk as master if no master already registered
        master_context = await self.rk.retrieve_master_bridge_context(
            context, bridge_id
        )
        if not master_context:
            self.rk.watch_key(
                "master",
                "bridges/{}/master".format(channel_entered.bridge.id),
                self._eheh,
            )
            self.rk.watch_key(
                "master", "bridges/{}/".format(channel_entered.bridge.id), self._eheh
            )

            await self.rk.register_master_bridge(context, channel_entered.bridge.id)
        elif master_context != context:
            # call the master asterisk if not already done
            channel_id = await self.rk.retrieve_slave_bridge_channel(context, bridge_id)

            if not channel_id:
                exten = channel_entered.channel.dialplan.exten
                if not exten:
                    logger.error(
                        "Unable to get exten called from application %s",
                        event.application_uuid,
                    )
                    return

                channel = await self.service.dial_asterisk_id(
                    context,
                    event.application_uuid,
                    master_context.asterisk_id,
                    exten,
                    caller_id=context.asterisk_id,
                    variables={RELATED_BRIDGE_ID_HEADER: bridge_id},
                    args="related_bridge_id,{}".format(bridge_id),
                )
                await self.rk.register_slave_bridge_channel(
                    context, bridge_id, channel.id
                )

    async def on_channel_left_bridge(
        self, context: Context, event: StasisEvent, channel_left: ChannelLeftBridge
    ) -> None:
        num = len(channel_left.bridge.channels)
        if num == 1:
            last_id = channel_left.bridge.channels[0]
            type = await self.service.get_channel_var(context, last_id, "type")
            if type == "related":
                await self.service.channel_hangup(context, last_id)
        elif num == 0:
            # NOTE(safchain) no more channel within the bridge remove it
            # is it really what we want to do ?
            await self.service.delete_bridge(context, channel_left.bridge.id)

    async def on_stasis_start(
        self, context: Context, event: StasisEvent, stasis_start: StasisStart
    ) -> None:
        if stasis_start.args:
            # if related(cross asterisk call) push the call to the bridge
            command, bridge_id = stasis_start.args
            if command == "related_bridge_id":
                return await self._answer_related_call(
                    context, stasis_start.channel, bridge_id
                )

        # if related(cross asterisk call) push the call to the bridge
        bridge_id = await self.service.get_channel_var(
            context,
            stasis_start.channel.id,
            "SIP_HEADER({})".format(RELATED_BRIDGE_ID_HEADER),
        )
        if bridge_id:
            return await self._answer_related_call(
                context, stasis_start.channel, bridge_id
            )

        if not stasis_start.args:
            return await self._start_user_outgoing_call(
                context, event.application_uuid, stasis_start
            )

        command, *command_args = stasis_start.args
        if command == "incoming":
            pass
        elif command == "originate":
            pass

    async def _start_user_outgoing_call(
        self, context: Context, application_uuid: str, stasis_start: StasisStart,
    ) -> None:
        logger.debug("New user outgoing call %s", stasis_start.channel.id)

        application = await self.service.get_application(context, application_uuid)
        call = await ApplicationCall.from_channel(context, stasis_start.channel)
        event = UserOutgoingCallCreated(self.config, context, application, call)
        self.bus.publish(event)

    async def _answer_related_call(
        self, context: Context, channel: Channel, node_uuid: str
    ) -> None:
        await self.service.channel_answer(context, channel.id)
        await self.service.set_channel_var(context, channel, "type", "related")

        logger.debug(
            "Add related call %s to the node %s on asterisk %s",
            channel.id,
            node_uuid,
            context.asterisk_id,
        )
        return await self.service.insert_channel_in_bridge(
            context, node_uuid, channel.id
        )
