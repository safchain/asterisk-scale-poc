# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class State(str, Enum):

    OK = "ok"
    KO = "ko"


class Status(BaseModel):

    state: State
