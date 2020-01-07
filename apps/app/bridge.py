import asyncio
import logging
import consul.aio
import swagger_client
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)


class BridgeMixin:

    async def get_or_create_bridge(self, context, id, type):
        bridges_api = swagger_client.BridgesApi(self.api_client)
        try:
            bridge = await bridges_api.bridges_bridge_id_get(
                id, x_asterisk_id=context.asterisk_id)

            logger.info("Bridge found on %s" % context.asterisk_id)

            return bridge
        except ApiException as e:
            pass

        try:
            bridge = await bridges_api.bridges_bridge_id_post(
                id, type=type, x_asterisk_id=context.asterisk_id)

            logger.info("Created a bridge on %s" % context.asterisk_id)
            return bridge
        except ApiException as e:
            logger.error("Error while creating bridge on %s : %s" %
                         (context.asterisk_id, e))

    async def dial(self, context, asterisk_id, extension):
        loop = asyncio.get_event_loop()

        c = consul.aio.Consul(
            host=self.config.consul_host,
            port=self.config.consul_port, loop=loop)

        (_, nodes) = await c.health.service("asterisk")
        for node in nodes:
            service = node.get("Service", {})
            meta = service.get("Meta", {})
            eid = meta.get("eid")

            if asterisk_id == eid:
                return await self._dial(context, "7001",
                                        service['Address'], service['Port'])

    async def _dial(self, context, extension, adddress, port):
        endpoint = "SIP/%s:%s/7001" % (adddress, port)

        logger.info("Dialing endpoint %s" % endpoint)
        try:
            channels_api = swagger_client.ChannelsApi(self.api_client)
            return await channels_api.channels_post(
                endpoint, app=self.id,
                x_asterisk_id=context.asterisk_id)
        except Exception as e:
            logger.error("Error while dialing endpoint %s : %s" %
                         (endpoint, e))

    async def _bridge_add_channel(self, context, bridge_id, channel_id):
        try:
            bridges_api = swagger_client.BridgesApi(self.api_client)
            await bridges_api.bridges_bridge_id_add_channel_post(
                bridge_id, [channel_id],
                x_asterisk_id=context.asterisk_id)

            logger.info("Added channel %s to bridge %s" %
                        (context.channel.id, bridge_id))
        except ApiException as e:
            logger.error("Error while add a channel to bridge %s : %s" %
                         (bridge_id, e))

    async def bridge_add_channel(self, context, bridge_id):
        return await self._bridge_add_channel(context,
                                              bridge_id, context.channel.id)
