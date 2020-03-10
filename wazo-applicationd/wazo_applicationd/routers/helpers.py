# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


from starlette.requests import Request
from starlette.responses import Response

from wazo_applicationd.config import Config
from wazo_applicationd.discovery import Discovery
from wazo_applicationd.service import Service
from wazo_applicationd.consul import Consul

from typing import cast


def get_service(request: Request) -> Service:
    return cast(Service, request.state.service)


def get_discovery(request: Request) -> Discovery:
    return cast(Discovery, request.state.discovery)


def get_config(request: Request) -> Config:
    return cast(Config, request.state.config)


def get_consul(request: Request) -> Consul:
    return cast(Consul, request.state.consul)
