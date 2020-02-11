# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import time

from typing import Awaitable

from .config import Config
from .application import ApplicationCall
from .context import Context
from .notifier import Notifier

from openapi_client import Configuration  # type: ignore
from openapi_client import ApiClient
from openapi_client import ApiException

from openapi_client.api.applications_api import ApplicationsApi  # type: ignore
from openapi_client.models.application import Application  # type: ignore

from openapi_client.api.channels_api import ChannelsApi  # type: ignore
from openapi_client.models.channel import Channel  # type: ignore

from openapi_client.exceptions import ApiException  # type: ignore

logger = logging.getLogger(__name__)


class Service:

    config: Config
    api_client: ApiClient
    notifier: Notifier

    def __init__(self, config: Config, notifier: Notifier) -> None:
        self.config = config
        self.notifier = notifier

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
    ) -> None:
        await self.set_channel_var_sync(
            context, channel, "WAZO_USER_OUTGOING_CALL", "true"
        )
        call = await ApplicationCall.from_channel(context, channel)
        await self.notifier.user_outgoing_call_created(context, application, call)
