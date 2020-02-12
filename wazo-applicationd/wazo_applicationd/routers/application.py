# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from fastapi import APIRouter  # type: ignore

from fastapi import Header  # type: ignore
from fastapi import Depends  # type: ignore

from typing import Any

from wazo_applicationd.config import Config
from wazo_applicationd.discovery import Discovery
from wazo_applicationd.context import Context
from wazo_applicationd.service import Service

from .request import get_config
from .request import get_discovery
from .request import get_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/applications/{name}")
async def register_application(
    name: str, discovery: Discovery = Depends(get_discovery)
) -> Any:
    await discovery.register_application(name)


@router.put("/applications/{app_uuid}/calls/{call_id}/answer")
async def answer_call(
    app_uuid: str,
    call_id: str,
    x_context_token: str = Header(None),
    config: Config = Depends(get_config),
    service: Service = Depends(get_service),
) -> Any:
    context = Context.from_token(config, x_context_token)
    logger.debug("asterisk id: {}".format(context.asterisk_id))

    await service.answer_call(context, call_id)
