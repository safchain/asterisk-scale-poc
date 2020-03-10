# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from typing import Awaitable, List, Union, Dict

from .discovery import Discovery
from .config import Config
from .context import Context
from .resources import ResourceManager
from .consul import Consul
from .exceptions import (
    ChannelCreateException,
    NoSuchChannelException,
    BridgeCreateException,
    BridgeJoinException,
    NoSuchBridgeException,
)

from .models.service import AsteriskNode

from wazo_appgateway_client import (  # type: ignore
    Configuration,
    ApiClient,
    ApiException,
)

from wazo_appgateway_client.api.applications_api import ApplicationsApi  # type: ignore
from wazo_appgateway_client.api.channels_api import ChannelsApi  # type: ignore
from wazo_appgateway_client.api.bridges_api import BridgesApi  # type: ignore

from wazo_appgateway_client.models.application import Application  # type: ignore
from wazo_appgateway_client.models.channel import Channel  # type: ignore
from wazo_appgateway_client.models.bridge import Bridge  # type: ignore

from wazo_appgateway_client.exceptions import ApiException  # type: ignore

logger = logging.getLogger(__name__)


class Service:

    config: Config
    discovery: Discovery
    rm: ResourceManager
    consul: Consul
    _api_client: ApiClient

    def __init__(
        self, config: Config, discovery: Discovery, rm: ResourceManager, consul: Consul
    ) -> None:
        self.config = config
        self.discovery = discovery
        self.consul = consul
        self.rm = rm

        configuration = Configuration()
        configuration.host = "%s/ari" % config.get("api_endpoint")
        configuration.username = config.get("api_username")
        configuration.password = config.get("api_password")

        self._api_client = ApiClient(configuration)

    async def get_application(
        self, context: Context, application_uuid: str
    ) -> Application:
        api = ApplicationsApi(self._api_client)
        return await api.applications_application_name_get(
            application_uuid, x_asterisk_id=context.asterisk_id
        )

    async def get_channel(
        self, context: Context, channel_id: str
    ) -> Union[Channel, None]:
        api = ChannelsApi(self._api_client)
        try:
            return await api.channels_channel_id_get(
                channel_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException as e:
           pass
        return None

    async def get_channel_var(
        self, context: Context, channel_id: str, var: str
    ) -> Union[str, None]:
        api = ChannelsApi(self._api_client)
        try:
            res = await api.channels_channel_id_variable_get(
                channel_id, var, x_asterisk_id=context.asterisk_id
            )
            return res.value
        except ApiException as e:
            pass
        return None

    async def set_channel_var(
        self, context: Context, channel: Channel, var: str, value: str
    ) -> None:
        api = ChannelsApi(self._api_client)
        await api.channels_channel_id_variable_post(
            channel.id, var, value=value, x_asterisk_id=context.asterisk_id
        )

    async def set_channel_var_sync(
        self, context: Context, channel: Channel, var: str, value: str, retry: int = 20
    ) -> None:
        api = ChannelsApi(self._api_client)
        try:
            await self.set_channel_var(context, channel, var, value)
        except ApiException as e:
            logging.error("Unable to set variable to channel %s: %s", channel.id, e)

        for _ in range(retry + 1):
            try:
                res = await api.channels_channel_id_variable_get(
                    channel.id, var, x_asterisk_id=context.asterisk_id
                )
                if res.value == value:
                    return
            except Exception as e:
                logger.debug("failed to get variable %s, %s", var, e)
            finally:
                logger.debug("waiting for a setvar to complete")
                await asyncio.sleep(0.1)

        raise Exception("failed to set channel variable %s=%s", var, value)

    async def channel_answer(self, context: Context, channel_id: str) -> None:
        logger.info("Answering channel %s", channel_id)

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_answer_post(
                channel_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchChannelException(channel_id)

    async def channel_mute_start(self, context: Context, channel_id: str) -> None:
        logger.info("Answering channel %s", channel_id)

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_mute_post(
                channel_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchChannelException(channel_id)

    async def channel_mute_stop(self, context: Context, channel_id: str) -> None:
        logger.info("Answering channel %s", channel_id)

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_mute_delete(
                channel_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchChannelException(channel_id)

    async def insert_channel_in_bridge(
        self, context: Context, bridge_id: str, channel_id: str
    ) -> None:
        api = BridgesApi(self._api_client)
        try:
            bridge = await api.bridges_bridge_id_get(
                bridge_id, x_asterisk_id=context.asterisk_id
            )

            await self._join_bridge(context, bridge.id, [channel_id])
        except ApiException:
            pass

    async def create_bridge_with_channels(
        self, bridge_id: str, channel_ids: List[str]
    ) -> str:
        ast_channels: Dict[str, List[str]] = {}
        for channel_id in channel_ids:
            context = await Context.from_resource_id(self.consul, channel_id)
            if not context:
                raise NoSuchChannelException(channel_id)

            id_list = ast_channels.get(context.asterisk_id)
            if id_list:
                id_list.append(channel_id)
            else:
                ast_channels[context.asterisk_id] = [channel_id]

        for asterisk_id, id_list in ast_channels.items():
            context = Context(asterisk_id=asterisk_id)
            await self._create_bridge_with_channels(context, bridge_id, id_list)

        return bridge_id

    async def _create_bridge_with_channels(
        self, context: Context, bridge_id: str, channel_ids: List[str],
    ) -> None:
        api = BridgesApi(self._api_client)

        if not channel_ids:
            raise BridgeCreateException()

        bridge = None
        try:
            bridge = await api.bridges_bridge_id_get(
                bridge_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            pass

        if not bridge:
            try:
                bridge = await api.bridges_bridge_id_post(
                    bridge_id, type="mixing", x_asterisk_id=context.asterisk_id
                )
            except ApiException:
                raise BridgeCreateException()

        curr_ids = set(bridge.channels)

        # compute the diff in order to insert only no existing channels
        add_ids = set(channel_ids) - curr_ids

        await self._join_bridge(context, bridge.id, list(add_ids))

    async def _join_bridge(
        self, context: Context, bridge_id: str, channel_ids: List[str]
    ) -> None:
        api = BridgesApi(self._api_client)
        try:
            await api.bridges_bridge_id_add_channel_post(
                bridge_id, channel_ids, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise BridgeJoinException()

    async def dial_asterisk_id(
        self,
        context: Context,
        application_uuid: str,
        asterisk_id: str,
        exten: str,
        caller_id: str = "",
        variables: Dict[str, str] = {},
        args: str = "",
    ) -> Channel:
        services = await self.discovery.retrieve_asterisk_nodes()
        for _, service in services.items():
            if asterisk_id == service.id:
                return await self._dial_node_exten(
                    context,
                    application_uuid,
                    service,
                    exten,
                    caller_id=caller_id,
                    variables=variables,
                    args=args,
                )

    async def _dial_node_exten(
        self,
        context: Context,
        application_uuid: str,
        node: AsteriskNode,
        exten: str,
        caller_id: str = "",
        variables: Dict[str, str] = {},
        args: str = "",
    ) -> Channel:
        endpoint = "SIP/{}:{}/{}".format(node.address, node.port, exten)

        logger.debug("Dialing endpoint %s", endpoint)

        api = ChannelsApi(self._api_client)
        return await api.channels_post(
            endpoint,
            app=application_uuid,
            app_args=args,
            caller_id=caller_id,
            x_asterisk_id=context.asterisk_id,
            containers={"variables": self._normalize_variables(variables)},
        )

    def _normalize_variables(self, variables: Dict[str, str]) -> Dict[str, str]:
        i = 0
        normalized: Dict[str, str] = {}

        for k, v in variables.items():
            h = "SIPADDHEADER{}".format(i)
            normalized[h] = "{}: {}".format(k, v)
            i = i + 1

        return normalized

    async def channel_hangup(self, context: Context, channel_id: str) -> None:
        logger.info("Hangup channel %s", channel_id)

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_delete(
                channel_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchChannelException(channel_id)

    async def delete_bridge(self, context: Context, bridge_id: str) -> None:
        api = BridgesApi(self._api_client)
        try:
            await api.bridges_bridge_id_delete(
                bridge_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchBridgeException(bridge_id)
