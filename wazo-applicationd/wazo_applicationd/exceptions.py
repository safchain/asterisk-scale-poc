# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any
from typing import Union


class APIException(Exception):

    status_code: int
    message: str
    error_id: str
    details: Any
    resource: Any

    def __init__(
        self,
        status_code: int,
        message: str,
        error_id: str,
        details: Any = None,
        resource: Any = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.id_ = error_id
        self.details = details or {}
        self.resource = resource


class ChannelCreateException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404,
            message="Channel create error",
            error_id="channel-create-error",
        )


class NoSuchChannelException(APIException):

    default_status_code: int = 404

    def __init__(self, channel_id: str, status_code: Union[int, None] = None) -> None:
        status_code = status_code or self.default_status_code
        super().__init__(
            status_code=status_code,
            message="No such channel",
            error_id="no-such-channel",
            details={"channel_id": channel_id},
        )


class BridgeCreateException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404,
            message="Bridge create error",
            error_id="bridge-create-error",
        )


class BridgeJoinException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404, message="Bridge join error", error_id="bridge-join-error",
        )


class NoSuchBridgeException(APIException):

    default_status_code: int = 404

    def __init__(self, bridge_id: str, status_code: Union[int, None] = None) -> None:
        status_code = status_code or self.default_status_code
        super().__init__(
            status_code=status_code,
            message="No such bridge",
            error_id="no-such-bridge",
            details={"bridge_id": bridge_id},
        )
