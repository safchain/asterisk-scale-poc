# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from typing import Awaitable, List, Union, Dict

from .resources import ResourceUUID, ResourceKeeper
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

from wazo_appgateway_client.api.applications_api import ApplicationsApi  # type: ignore
from wazo_appgateway_client.api.channels_api import ChannelsApi  # type: ignore
from wazo_appgateway_client.api.bridges_api import BridgesApi  # type: ignore

from wazo_appgateway_client.models.application import Application  # type: ignore
from wazo_appgateway_client.models.channel import Channel  # type: ignore
from wazo_appgateway_client.models.bridge import Bridge  # type: ignore

from wazo_appgateway_client.exceptions import ApiException  # type: ignore

logger = logging.getLogger(__name__)

RELATED_NODE_UUID_HEADER = "X-Related-Node-UUID"


class Service:

    config: Config
    rk: ResourceKeeper
    discovery: Discovery
    _api_client: ApiClient

    def __init__(
        self, config: Config, discovery: Discovery, rk: ResourceKeeper
    ) -> None:
        self.config = config
        self.rk = rk
        self.discovery = discovery

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

    async def get_channel(self, context: Context, call_id: str) -> Union[Channel, None]:
        api = ChannelsApi(self._api_client)
        try:
            return await api.channels_channel_id_get(
                call_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException as e:
            logging.error("Unable to get channel {} : {}".format(call_id, e))
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
            logging.error(
                "Unable to get variable to channel {} : {}".format(channel_id, e)
            )
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
            logging.error(
                "Unable to set variable to channel {} : {}".format(channel.id, e)
            )

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
            return await ApplicationCall.from_channel(context, channel)
        except Exception:
            raise CallCreateException()

    async def call_answer(self, context: Context, call_id: str) -> None:
        logger.info("Answering call {}".format(call_id))

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_answer_post(
                call_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchCallException(call_id)

    async def insert_call_to_node(
        self, context: Context, node_uuid: str, call_id: str
    ) -> None:
        api = BridgesApi(self._api_client)
        try:
            bridge = await api.bridges_bridge_id_get(
                node_uuid, x_asterisk_id=context.asterisk_id
            )

            await self._join_bridge(context, bridge.id, [call_id])
        except ApiException:
            pass

    async def create_node_with_calls(
        self,
        context: Context,
        application_uuid: str,
        node_name: str,
        call_ids: List[str],
    ) -> ApplicationNode:
        node_uuid = ResourceUUID(application_uuid, node_name)

        api = BridgesApi(self._api_client)

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

        curr_ids = set(bridge.channels)

        # compute the diff in order to insert only no existing channels
        add_ids = set(call_ids) - curr_ids

        # compute the list of current call ids
        full_ids = list(curr_ids | add_ids)

        await self._join_bridge(context, bridge.id, list(add_ids))

        node = ApplicationNode(uuid=node_uuid, call_ids=full_ids)

        master_context = await self.rk.retrieve_master_node_context(node.uuid)
        if not master_context:
            await self.rk.register_master_node(context, node)
        elif master_context.asterisk_id != context.asterisk_id:
            # TODO(safchain) do not hard code extension
            await self._link_master_node(
                context,
                application_uuid,
                master_context.asterisk_id,
                "6001",
                caller_id=node_uuid,
                variables={RELATED_NODE_UUID_HEADER: node_uuid},
            )

        return node

    async def _link_master_node(
        self,
        context: Context,
        application_uuid: str,
        master_id: str,
        exten: str,
        caller_id: str = "",
        variables: Dict[str, str] = {},
    ) -> None:
        logger.info("start linking asterisk instances")

        # TODO(safchain) check if not already linked, master election ??
        await self._dial_asterisk_id(
            context,
            application_uuid,
            master_id,
            exten,
            caller_id=caller_id,
            variables=variables,
        )

    async def _join_bridge(
        self, context: Context, bridge_id: str, call_ids: List[str]
    ) -> None:
        api = BridgesApi(self._api_client)
        try:
            await api.bridges_bridge_id_add_channel_post(
                bridge_id, call_ids, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NodeJoinException()

    async def _dial_asterisk_id(
        self,
        context: Context,
        application_name: str,
        asterisk_id: str,
        exten: str,
        caller_id: str = "",
        variables: Dict[str, str] = {},
    ) -> None:
        services = await self.discovery.retrieve_asterisk_services()
        for service in services:
            if asterisk_id == service.id:
                await self._dial_service_exten(
                    context,
                    application_name,
                    service,
                    exten,
                    caller_id=caller_id,
                    variables=variables,
                )

    async def _dial_service_exten(
        self,
        context: Context,
        application_uuid: str,
        service: AsteriskService,
        exten: str,
        caller_id: str = "",
        variables: Dict[str, str] = {},
    ) -> None:
        # endpoint = "PJSIP/outgoing/sip:{}:1@{}:{}".format(exten, service.address, service.port)
        endpoint = "SIP/%s:%s/%s" % (service.address, service.port, exten)

        logger.info("Dialing endpoint %s" % endpoint)

        api = ChannelsApi(self._api_client)
        await api.channels_post(
            endpoint,
            app=application_uuid,
            app_args="related",
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

    async def get_related_node_uuid(
        self, context: Context, channel: Channel
    ) -> Union[str, None]:
        return await self.get_channel_var(
            context, channel.id, "SIP_HEADER({})".format(RELATED_NODE_UUID_HEADER),
        )

    async def call_hangup(self, context: Context, call_id: str) -> None:
        logger.info("Hangup call {}".format(call_id))

        api = ChannelsApi(self._api_client)
        try:
            await api.channels_channel_id_delete(
                call_id, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NoSuchCallException(call_id)

    async def delete_node(self, context: Context, node_uuid: str) -> None:
        api = BridgesApi(self._api_client)
        try:
            await api.bridges_bridge_id_delete(
                node_uuid, x_asterisk_id=context.asterisk_id
            )
        except ApiException:
            raise NodeJoinException()
