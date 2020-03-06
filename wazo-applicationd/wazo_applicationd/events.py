# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json

from typing import Dict
from typing import Any
from typing import Union

from wazo_appgateway_client.models.application import Application  # type: ignore

from .models.application import Application as WazoApplication
from .models.application import ApplicationCall

from .schemas import application_call_schema
from .context import Context
from .config import Config


class BaseEvent:

    required_acl_tmpl: str = "events.{}"

    name: str
    routing_key: str
    required_acl: Union[str, None]
    application_uuid: str
    origin_uuid: str
    body: Dict[str, Any]

    def __init__(self, config: Config, context: Context, application: Application):
        self.application_uuid = application.name
        self.origin_uuid = config.get("uuid")
        self.required_acl = None

        self.body = {
            "name": self.name,
            "origin_uuid": self.origin_uuid,
            "data": {
                # NOTE(safchain) not useful anymore as now use KV
                # "context_token": context.to_token(config),
                "application_uuid": self.application_uuid,
            },
        }

    @property
    def metadata(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "origin_uuid": self.origin_uuid,
        }

        if self.required_acl is not None:
            result["required_acl"] = self.required_acl

        return result


class BaseCallItemEvent(BaseEvent):
    def __init__(
        self,
        config: Config,
        context: Context,
        application: Application,
        call: ApplicationCall,
    ) -> None:
        super().__init__(config, context, application)

        self.routing_key = self.routing_key.format(self.application_uuid, call.id)
        self.required_acl = self.required_acl_tmpl.format(self.routing_key)
        self.body["data"]["call"] = application_call_schema.dump(call)


class UserOutgoingCallCreated(BaseCallItemEvent):
    name = "user_outgoing_call_created"
    routing_key = "applications.{}.user_outgoing_call.{}.created"
