# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from fastapi import APIRouter  # type: ignore
from fastapi import Header  # type: ignore
from fastapi import Depends  # type: ignore

from typing import List

from wazo_applicationd.config import Config
from wazo_applicationd.discovery import Discovery
from wazo_applicationd.context import Context
from wazo_applicationd.service import Service
from wazo_applicationd.consul import Consul
from wazo_applicationd import helpers

from wazo_applicationd.models.application import Application
from wazo_applicationd.models.node import Node

from .helpers import get_discovery
from .helpers import get_service
from .helpers import get_consul

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/applications/{application_name}", response_model=Application)
async def register_application(
    application_name: str, discovery: Discovery = Depends(get_discovery)
) -> Application:
    return await discovery.register_application(application_name)


@router.put("/applications/{application_uuid}/calls/{call_id}/answer")
async def call_answer(
    application_uuid: str,
    call_id: str,
    consul: Consul = Depends(get_consul),
    service: Service = Depends(get_service),
) -> None:
    context = await Context.from_resource_id(consul, call_id)
    await service.channel_answer(context, call_id)


@router.post("/applications/{application_uuid}/nodes/{node_name}", response_model=Node)
async def create_node_with_calls(
    application_uuid: str,
    node_name: str,
    call_ids: List[str],
    consul: Consul = Depends(get_consul),
    service: Service = Depends(get_service),
) -> Node:
    bridge_id = helpers.resource_uuid(application_uuid, node_name)
    await service.create_bridge_with_channels(bridge_id, call_ids)
    return Node(uuid=bridge_id)


@router.post("/applications/{application_uuid}/calls/{call_id}/mute/start")
async def call_mute_start(
    application_uuid: str,
    call_id: str,
    consul: Consul = Depends(get_consul),
    service: Service = Depends(get_service),
):
    context = await Context.from_resource_id(consul, call_id)
    await service.channel_mute_start(context, call_id)


@router.post("/applications/{application_uuid}/calls/{call_id}/mute/stop")
async def call_mute_stop(
    application_uuid: str,
    call_id: str,
    consul: Consul = Depends(get_consul),
    service: Service = Depends(get_service),
):
    context = await Context.from_resource_id(consul, call_id)
    await service.channel_mute_stop(context, call_id)


@router.delete("/applications/{application_uuid}/calls/{call_id}")
async def call_hangup(
    application_uuid: str,
    call_id: str,
    consul: Consul = Depends(get_consul),
    service: Service = Depends(get_service),
) -> None:
    context = await Context.from_resource_id(consul, call_id)
    await service.channel_hangup(context, call_id)

