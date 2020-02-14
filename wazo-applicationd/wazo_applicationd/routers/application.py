# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from fastapi import APIRouter

from fastapi import Header
from fastapi import Depends

from typing import List

from wazo_applicationd.config import Config
from wazo_applicationd.discovery import Discovery
from wazo_applicationd.context import Context
from wazo_applicationd.service import Service

from wazo_applicationd.models.application import Application
from wazo_applicationd.models.node import ApplicationNode

from .request import get_config
from .request import get_discovery
from .request import get_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/applications/{application_uuid}", response_model=Application)
async def register_application(
    application_uuid: str, discovery: Discovery = Depends(get_discovery)
) -> Application:
    return await discovery.register_application(application_uuid)


@router.put("/applications/{application_uuid}/calls/{call_id}/answer")
async def call_answer(
    application_uuid: str,
    call_id: str,
    x_context_token: str = Header(None),
    config: Config = Depends(get_config),
    service: Service = Depends(get_service),
) -> None:
    context = Context.from_token(config, x_context_token)
    await service.call_answer(context, call_id)


@router.post("/applications/{application_uuid}/nodes", response_model=ApplicationNode)
async def create_node_with_calls(
    application_uuid: str,
    call_ids: List[str],
    x_context_token: str = Header(None),
    config: Config = Depends(get_config),
    service: Service = Depends(get_service),
) -> ApplicationNode:
    context = Context.from_token(config, x_context_token)
    application_name = Application.uuid_to_name(application_uuid)
    await service.create_node_with_calls(context, application_name, call_ids)
