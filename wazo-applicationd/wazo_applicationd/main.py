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
from .resources import ResourceManager
from .leader import LeaderManager

logger = logging.getLogger(__name__)


def run(config: Config) -> None:
    leader = LeaderManager(config)
    discovery = Discovery(config, leader)
    bus = Bus(config)
    rm = ResourceManager(config, discovery)
    service = Service(config, discovery, rm)
    stasis = Stasis(config, bus, service, discovery, rm)
    api = API(config, discovery, service)

    stasis.subscribe_events()

    loop = asyncio.get_event_loop()

    api_task = loop.create_task(api.run())
    bus_task = loop.create_task(bus.run())
    discovery_task = loop.create_task(discovery.run())

    try:
        loop.run_until_complete(api_task)
    finally:
        bus_task.cancel()
        discovery_task.cancel()

        loop.run_until_complete(bus_task)
        loop.run_until_complete(discovery_task)

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
