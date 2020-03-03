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
from wazo_applicationd.resources import ResourceUUID

from wazo_applicationd.models.application import Application
from wazo_applicationd.models.node import Node

from .helpers import get_config
from .helpers import get_discovery
from .helpers import get_service

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
    x_context_token: str = Header(None),
    config: Config = Depends(get_config),
    service: Service = Depends(get_service),
) -> None:
    context = Context.from_token(config, x_context_token)
    await service.channel_answer(context, call_id)


@router.post("/applications/{application_uuid}/nodes/{node_name}", response_model=Node)
async def create_bridge_with_calls(
    application_uuid: str,
    node_name: str,
    call_ids: List[str],
    x_context_token: str = Header(None),
    config: Config = Depends(get_config),
    service: Service = Depends(get_service),
) -> Node:
    context = Context.from_token(config, x_context_token)
    bridge_id = ResourceUUID(application_uuid, node_name)
    await service.create_bridge_with_channels(
        context, application_uuid, bridge_id, call_ids
    )
    return Node(uuid=bridge_id)

