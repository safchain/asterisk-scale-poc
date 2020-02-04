# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Dict
from typing import Any

from openapi_client.models.application import Application  # type: ignore

from .application import Application as WazoApplication
from .application import ApplicationCall
from .schemas import application_call_schema


class BaseEvent:

    routing_key: str
    required_acl: str = "events.{}"
    body: Dict[str, Any]

    def marshal(self) -> Dict[str, Any]:
        return self.body


class BaseCallItemEvent(BaseEvent):
    def __init__(
        self, application: Application, call: ApplicationCall
    ) -> None:
        uuid = WazoApplication.name_to_uuid(application.name)

        self.routing_key = self.routing_key.format(uuid, call.id)
        self.required_acl = self.required_acl.format(self.routing_key)
        self.body = {
            "application_uuid": uuid,
            "call": application_call_schema.dump(call),
        }


class UserOutgoingCallCreated(BaseCallItemEvent):
    name = "application_user_outgoing_call_created"
    routing_key = "applications.{}.user_outgoing_call.{}.created"
