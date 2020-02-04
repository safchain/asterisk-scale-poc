# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from openapi_client.models.application import Application  # type: ignore

from .bus import Bus
from .application import ApplicationCall
from .events import UserOutgoingCallCreated

logger = logging.getLogger(__name__)


class Notifier:

    bus: Bus

    def __init__(self, bus: Bus) -> None:
        self.bus = bus

    async def user_outgoing_call_created(
        self, application: Application, call: ApplicationCall
    ) -> None:
        logger.debug(
            "Application {}: User outgoing call {} created".format(
                application.name, call.id
            )
        )

        event = UserOutgoingCallCreated(application, call)
        print("#######")
        print(event.body)
        print("#######")
        # self._bus.publish(event)
