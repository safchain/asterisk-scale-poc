# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from marshmallow import (
    EXCLUDE,
    Schema,
    fields,
    pre_dump,
    pre_load,
    post_load,
)

from typing import Any
from typing import Mapping


class StrictDict(fields.Dict):

    key_field: fields.Field
    value_field: fields.Field

    def __init__(
        self,
        key_field: fields.Field,
        value_field: fields.Field,
        *args: Any,
        **kwargs: Any
    ):
        super().__init__(*args, **kwargs)

        self.key_field = key_field
        self.value_field = value_field

    def _deserialize(self, value: Any, attr: str = None, data: Mapping[str, Any] = None, **kwargs: Any):
        values = super()._deserialize(value, attr, data, **kwargs)

        result = {}
        for key, value in values.items():
            new_key = self.key_field.deserialize(key, attr, data)
            new_value = self.value_field.deserialize(value, attr, data)
            result[new_key] = new_value
        return result


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    @pre_load
    def ensure_dict(self, data):
        return data or {}


class ApplicationCallSchema(BaseSchema):
    id = fields.String(attribute="id")
    caller_id_name = fields.String()
    caller_id_number = fields.String()
    creation_time = fields.String()
    status = fields.String()
    on_hold = fields.Boolean()
    is_caller = fields.Boolean()
    dialed_extension = fields.String()
    variables = StrictDict(key_field=fields.String(), value_field=fields.String())
    node_uuid = fields.String()
    moh_uuid = fields.String()
    muted = fields.Boolean()
    snoops = fields.Dict(dump_only=True)
    user_uuid = fields.String()
    tenant_uuid = fields.String()


application_call_schema = ApplicationCallSchema()
