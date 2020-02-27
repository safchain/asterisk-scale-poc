# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import uuid

from typing import Union

RESOURCE_UUID_NAMESPACE = uuid.UUID("bcfcc0df-a4a4-40fb-b760-f25eea31e95d")


def ResourceUUID(application: str, value: Union[str, None] = None) -> str:
    if value:
        return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application + "-" + value))
    return str(uuid.uuid5(RESOURCE_UUID_NAMESPACE, application))
