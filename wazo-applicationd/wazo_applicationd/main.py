# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import logging
import argparse
import sys

from typing import Type
from types import TracebackType

from .config import Config
from .bus import Bus
from .api import API
from .discovery import Discovery
from .stasis import Stasis
from .service import Service
from .resources import ResourceKeeper

from wazo_appgateway_client.models import Message  # type: ignore

logger = logging.getLogger(__name__)


def run(config: Config) -> None:
    discovery = Discovery(config)
    bus = Bus(config)
    rk = ResourceKeeper(config)
    service = Service(config, discovery, rk)
    stasis = Stasis(config, bus, service, discovery, rk)
    api = API(config, discovery, service)

    stasis.subscribe_events()

    loop = asyncio.get_event_loop()

    api_task = loop.create_task(api.run())
    bus_task = loop.create_task(bus.run())
    rk_task = loop.create_task(rk.run())
    discovery_task = loop.create_task(discovery.run())

    try:
        loop.run_until_complete(api_task)
    finally:
        bus_task.cancel()
        discovery_task.cancel()
        rk_task.cancel()

        loop.run_until_complete(bus_task)
        loop.run_until_complete(discovery_task)
        loop.run_until_complete(rk_task)

        loop.close()


def excepthook(
    type_: Type[BaseException], value: BaseException, traceback: TracebackType
) -> None:
    logging.critical(value, exc_info=(type_, value, traceback))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", default="", help="application config file")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    config = Config()

    if args.debug:
        config.override("debug", True)

    sys.excepthook = excepthook

    if args.conf:
        config.load_file(args.conf)

    run(config)
