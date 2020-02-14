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


class CallCreateException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404, message="Call create error", error_id="call-create-error",
        )


class NoSuchCallException(APIException):

    default_status_code: int = 404

    def __init__(self, call_id: str, status_code: Union[int, None] = None) -> None:
        status_code = status_code or self.default_status_code
        super().__init__(
            status_code=status_code,
            message="No such call",
            error_id="no-such-call",
            details={"call_id": call_id},
        )


class NodeCreateException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404, message="Node create error", error_id="node-create-error",
        )


class NodeJoinException(APIException):
    def __init__(self):
        super().__init__(
            status_code=404, message="Node join error", error_id="node-join-error",
        )
