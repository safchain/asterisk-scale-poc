# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json

from typing import Dict
from typing import Any
from typing import Union

from openapi_client.models.application import Application  # type: ignore

from .application import Application as WazoApplication
from .application import ApplicationCall
from .schemas import application_call_schema
from .context import Context
from .config import Config

"""
class Marshaler(object):

    content_type = 'application/json'

    def __init__(self, uuid):
        self._uuid = uuid

    def metadata(self, command):
        result = {
            'name': command.name,
            'origin_uuid': self._uuid,
        }

        if hasattr(command, 'required_acl'):
            result['required_acl'] = command.required_acl

        return result

    def marshal_message(self, command):
        body = dict(self.metadata(command))
        body['data'] = command.marshal()
        return json.dumps(body)

    @classmethod
    def unmarshal_message(cls, obj, event_class):
        if not isinstance(obj, dict):
            raise InvalidMessage(obj)
        if 'data' not in obj:
            raise InvalidMessage(obj)
        if 'origin_uuid' not in obj:
            raise InvalidMessage(obj)

        event = event_class.unmarshal(obj['data'])
        event.metadata = {'origin_uuid': obj['origin_uuid']}
        return event
"""


class BaseEvent:

    required_acl_tmpl: str = "events.{}"

    name: str
    routing_key: str
    required_acl: Union[str, None]
    application_uuid: str
    origin_uuid: str
    data: Dict[str, Any]

    def __init__(self, config: Config, context: Context, application: Application):
        self.application_uuid = WazoApplication.name_to_uuid(application.name)
        self.origin_uuid = config.get("uuid")
        self.required_acl = None

        # NOTE(safchain) with a better way to pass the asterisk id, JWT ???
        self.data = {
            "context": context.asterisk_id,
            "application_uuid": self.application_uuid,
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

    @property
    def body(self) -> Dict[str, Any]:
        return self.data or {}


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
        self.data["call"] = application_call_schema.dump(call)


class UserOutgoingCallCreated(BaseCallItemEvent):
    name = "application_user_outgoing_call_created"
    routing_key = "applications.{}.user_outgoing_call.{}.created"
