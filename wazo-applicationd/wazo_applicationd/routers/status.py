# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter  # type: ignore
from fastapi import Depends  # type: ignore

from pydantic import BaseModel

from wazo_applicationd.models.status import State
from wazo_applicationd.models.status import Status
from wazo_applicationd.discovery import Discovery

from .helpers import get_discovery

router = APIRouter()


@router.get("/status", response_model=Status)
async def status() -> Status:
    return Status(state=State.OK)