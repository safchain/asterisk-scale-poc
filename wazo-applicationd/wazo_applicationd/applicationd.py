# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging

from .config import Config
from .bus import Bus
from .api import API
from .discovery import Discovery
from .stasis import Stasis
from .notifier import Notifier
from .service import Service

from swagger_client.models import Message  # type: ignore

logger = logging.getLogger(__name__)


class Applicationd:

    config: Config
    bus: Bus
    api: API
    discovery: Discovery
    stasis: Stasis
    notifier: Notifier
    service: Service

    def __init__(self, config: Config) -> None:
        self.config = config

        self.discovery = Discovery(config)
        self.api = API(config, self.discovery)
        self.bus = Bus(config)
        self.notifier = Notifier(self.bus)
        self.service = Service(config, self.notifier)
        self.stasis = Stasis(self.bus, self.service)

    async def run(self) -> None:
        self.stasis.subscribe_events()

        await asyncio.gather(
            self.bus.run(), self.api.run(), self.discovery.run()
        )
