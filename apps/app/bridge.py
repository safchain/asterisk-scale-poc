import asyncio
import logging
import consul.aio
import swagger_client
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)


class BridgeMixin:

    def __init__(self, *args, **kwargs):
        super(BridgeMixin, self).__init__()

        self.master_bridges = dict()
        self.dial_bridges = set()

    async def get_or_create_bridge(self, context, id, type):
        bridges_api = swagger_client.BridgesApi(self.api_client)
        try:
            bridge = await bridges_api.bridges_bridge_id_get(
                id, x_asterisk_id=context.asterisk_id)

            logger.info("Bridge found on %s" % context.asterisk_id)

            await self._mesh(context, id)

            return bridge
        except ApiException as e:
            pass

        try:
            bridge = await bridges_api.bridges_bridge_id_post(
                id, type=type, x_asterisk_id=context.asterisk_id)

            if id not in self.master_bridges:
                self.master_bridges[id] = context.asterisk_id

            logger.info("Created a bridge on %s" % context.asterisk_id)

            await self._mesh(context, id)

            return bridge
        except ApiException as e:
            logger.error("Error while creating bridge on %s : %s" %
                         (context.asterisk_id, e))

    async def _mesh(self, context, id):
        master = self.master_bridges.get(id)
        if not master:
            return

        if context.asterisk_id == master:
            return

        if context.channel.id in self.dial_bridges:
            return

        channel = await self._dial_asterisk(
            context, self.master, context.channel.exten)
        if channel:
            self.dial_bridges.add(channel.id)

    async def bridge_add_channel(self, context, id):
        try:
            bridges_api = swagger_client.BridgesApi(self.api_client)
            await bridges_api.bridges_bridge_id_add_channel_post(
                id, [context.channel.id],
                x_asterisk_id=context.asterisk_id)

            logger.info("Added channel %s to bridge %s" %
                        (context.channel.id, id))
        except ApiException as e:
            logger.error("Error while add a channel to bridge %s : %s" %
                         (id, e))
