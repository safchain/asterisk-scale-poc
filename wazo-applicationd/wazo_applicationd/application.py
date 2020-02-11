# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from openapi_client.models.channel import Channel  # type: ignore

from .context import Context


class Application:

    PREFIX: str = "wazo-app-"

    @staticmethod
    def name_to_uuid(name: str) -> str:
        if not name or not name.startswith(Application.PREFIX):
            return ""
        return name[len(Application.PREFIX) :]

    @staticmethod
    def is_valid(name: str) -> bool:
        return name != None and name.startswith(Application.PREFIX)


class ApplicationCall:

    id: str
    creation_time: str
    status: str
    caller_id_name: str
    caller_id_number: str
    moh_uuid: str
    muted: bool
    user_uuid: str
    tenant_uuid: str
    # snoops: Dict

    @classmethod
    async def from_channel(self, context: Context, channel: Channel) -> ApplicationCall:
        call = ApplicationCall()

        call.id = channel.id
        call.creation_time = channel.creationtime
        call.status = channel.state
        call.caller_id_name = channel.caller.name
        call.caller_id_number = channel.caller.number

        # call.snoops = self._get_snoops(channel)

        """
        if node_uuid:
            call.node_uuid = node_uuid

        if self._ari is not None:
            channel_helper = _ChannelHelper(channel.id, self._ari)
            call.on_hold = channel_helper.on_hold()
            call.is_caller = channel_helper.is_caller()
            call.dialed_extension = channel_helper.dialed_extension()
            try:
                call.moh_uuid = channel.getChannelVar(variable='WAZO_MOH_UUID').get('value') or None
            except ARINotFound:
                call.moh_uuid = None

            try:
                call.user_uuid = channel.getChannelVar(variable='XIVO_USERUUID').get('value')
            except ARINotFound:
                call.user_uuid = None

            try:
                call.tenant_uuid = channel.getChannelVar(variable='WAZO_TENANT_UUID').get('value')
            except ARINotFound:
                call.tenant_uuid = None

            try:
                call.muted = channel.getChannelVar(variable='WAZO_CALL_MUTED').get('value') == '1'
            except ARINotFound:
                call.muted = False

            call.node_uuid = getattr(call, 'node_uuid', None)
            for bridge in self._ari.bridges.list():
                if channel.id in bridge.json['channels']:
                    call.node_uuid = bridge.id
                    break

            if call.status == 'Ring' and channel_helper.is_progress():
                call.status = 'Progress'

        if variables is not None:
            call.variables = variables
        """

        return call
