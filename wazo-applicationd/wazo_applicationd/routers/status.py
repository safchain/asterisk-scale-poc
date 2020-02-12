# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from fastapi import APIRouter  # type: ignore

from typing import Any

router = APIRouter()


@router.get("/status")
async def status() -> Any:
    return {"state": "ok"}
