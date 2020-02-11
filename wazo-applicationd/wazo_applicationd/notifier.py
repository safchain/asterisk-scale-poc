# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from openapi_client.models.application import Application  # type: ignore

from .bus import Bus
from .application import ApplicationCall
from .events import UserOutgoingCallCreated
from .context import Context
from .config import Config

logger = logging.getLogger(__name__)


class Notifier:

    config: Config
    bus: Bus

    def __init__(self, config: Config, bus: Bus) -> None:
        self.bus = bus
        self.config = config

    async def user_outgoing_call_created(
        self, context: Context, application: Application, call: ApplicationCall
    ) -> None:
        logger.debug(
            "Application {}: User outgoing call {} created".format(
                application.name, call.id
            )
        )

        event = UserOutgoingCallCreated(self.config, context, application, call)
        self.bus.publish(event)
