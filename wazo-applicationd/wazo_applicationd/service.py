# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import time

from typing import Awaitable
from typing import List

from .discovery import Discovery
from .config import Config
from .context import Context
from .exceptions import (
    CallCreateException,
    NoSuchCallException,
    NodeCreateException,
    NodeJoinException,
)

from .models.application import ApplicationCall
from .models.node import ApplicationNode
from .models.service import AsteriskService

from wazo_appgateway_client import (  # type: ignore
    Configuration,
    ApiClient,
    ApiException,
)

from wazo_appgateway_client.api.applications_api import (  # type: ignore
    ApplicationsApi,
    ChannelsApi,
    BridgesApi,
)

from wazo_appgateway_client.models.application import (  # type: ignore
    Application,
    Channel,
    Bridge,
)

from wazo_appgateway_client.exceptions import ApiException  # type: ignore

logger = logging.getLogger(__name__)


class Service:

    config: Config
    api_client: ApiClient

    def __init__(self, config: Config, discovery: Discovery) -> None:
        self.config = config
        self.discovery = discovery

        configuration = Configuration()
        configuration.host = "%s/ari" % config.get("api_endpoint")
        configuration.username = config.get("api_username")
        configuration.password = config.get("api_password")

        self.api_client = ApiClient(configuration)

    async def get_application(
        self, context: Context, application_name: str
    ) -> Application:
        api = ApplicationsApi(self.api_client)
        return await api.applications_application_name_get(
            application_name, x_asterisk_id=context.asterisk_id
        )

    async def set_channel_var_sync(
        self, context: Context, channel: Channel, var: str, value: str, retry: int = 20,
    ) -> None:
        api = ChannelsApi(self.api_client)
        try:
            await api.channels_channel_id_variable_post(
                channel.id, var, value=value, x_asterisk_id=context.asterisk_id
            )
        except ApiException as e:
            logging.error(
                "Unable to set variable to channel {} : {}".format(channel.id, e)
            )
            return

        # TODO remove this when Asterisk gets fixed to set var synchronously
        for _ in range(retry + 1):
            try:
                res = await api.channels_channel_id_variable_get(
                    channel.id, var, x_asterisk_id=context.asterisk_id
                )
                if res.value == value:
                    return
            except Exception as e:
                logger.debug("failed to get variable {} : {}".format(var, e))
            finally:
                logger.debug("waiting for a setvar to complete")
                await asyncio.sleep(0.1)

        raise Exception("failed to set channel variable {}={}".format(var, value))

    async def start_user_outgoing_call(
        self, context: Context, application: Application, channel: Channel
    ) -> ApplicationCall:
        try:
            await self.set_channel_var_sync(
                context, channel, "WAZO_USER_OUTGOING_CALL", "true"
            )
            return await ApplicationCall.from_channel(context, channel)
        except Exception:
            raise CallCreateException()

    async def call_answer(self, context: Context, call_id: str) -> None:
        logger.info("Answering call on channel : %s" % context)

        api = ChannelsApi(self.api_client)
        try:
            await api.channels_channel_id_answer_post(
                call_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchCallException(call_id)

    async def create_node_with_calls(
        self, context: Context, application_name: str, call_ids: List[str]
    ) -> ApplicationNode:
        # NOTE(safchain) not sure about this, should we generate UUID ?
        node_uuid = application_name

        api = BridgesApi(self.api_client)

        bridge = None
        try:
            bridge = await api.bridges_bridge_id_get(
                node_uuid, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            pass

        if not bridge:
            try:
                bridge = await api.bridges_bridge_id_post(
                    node_uuid, type="mixing", x_asterisk_id=context.asterisk_id
                )
            except ApiException:
                raise NodeCreateException()

        await self._join_bridge(context, bridge.id, call_ids)

        node = ApplicationNode(uuid=node_uuid, call_ids=call_ids)

        # TODO(safchain) !important, this should be atomic
        master_context = await self.discovery.retrieve_master_node_context(node)
        if not master_context:
            await self.discovery.register_master_node(context, node)
        elif master_context.asterisk_id != context.asterisk_id:
            # TODO(safchain) do not hard code extension
            await self._mesh(
                context, application_name, master_context.asterisk_id, "6001"
            )

        return node

    async def _mesh(
        self, context: Context, application_name: str, master_id: str, exten: str,
    ) -> None:
        logger.info("start meshing")

        # TODO(safchain) check if not already linked
        channel = await self._dial_asterisk(context, application_name, master_id, exten)

    async def _join_bridge(
        self, context: Context, bridge_id: str, call_ids: List[str]
    ) -> None:
        api = BridgesApi(self.api_client)
        try:
            await api.bridges_bridge_id_add_channel_post(
                bridge_id, call_ids, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NodeJoinException()

    async def _dial_asterisk(
        self, context: Context, application_name: str, asterisk_id: str, exten: str
    ) -> None:
        services = await self.discovery.retrieve_asterisk_services()
        for service in services:
            if asterisk_id == service.id:
                await self._dial_service_exten(
                    context, application_name, service, exten
                )

    async def _dial_service_exten(
        self,
        context: Context,
        application_name: str,
        service: AsteriskService,
        exten: str,
    ) -> None:
        endpoint = "SIP/{}:{}/{}".format(service.address, service.port, exten)

        logger.info("Dialing endpoint %s" % endpoint)

        api = ChannelsApi(self.api_client)
        r = await api.channels_post(
            endpoint,
            app=application_name,
            x_asterisk_id=context.asterisk_id,
            containers={"variables": {}},
        )
