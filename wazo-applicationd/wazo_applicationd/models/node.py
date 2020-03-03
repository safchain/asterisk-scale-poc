# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Node(BaseModel):

    uuid: str
