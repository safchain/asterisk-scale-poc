import asyncio
import logging
import consul.aio
import swagger_client
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)


class Channel:

    def __init__(self, obj):
        self.obj = obj

    @property
    def dialplan(self):
        return self.obj.get('dialplan', {})

    @property
    def id(self):
        return self.obj.get('id')

    @property
    def state(self):
        return self.obj.get('state')

    @property
    def raw(self):
        return self.obj

    @property
    def exten(self):
        return self.dialplan.get('exten')


class ChannelMixin:

    def __init__(self, *args, **kwargs):
        super(ChannelMixin, self).__init__()

    async def answer(self, context):
        logger.info("Answering call on channel : %s" % context)

        try:
            channels_api = swagger_client.ChannelsApi(self.api_client)
            await channels_api.channels_channel_id_answer_post(
                context.channel.id, x_asterisk_id=context.asterisk_id)

            logger.info("Answered channel %s successful" % context)
        except Exception as e:
            logger.error("Error while answering channel %s : %s" % (
                context, e))

    async def _dial_asterisk(self, context, asterisk_id, extension):
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
                return await self._dial(context, extension,
                                        service['Address'], service['Port'])

    async def _dial(self, context, extension, adddress, port):
        endpoint = "SIP/%s:%s/%s" % (adddress, port, extension)

        logger.info("Dialing endpoint %s" % endpoint)
        try:
            channels_api = swagger_client.ChannelsApi(self.api_client)
            return await channels_api.channels_post(
                endpoint, app=self.id,
                x_asterisk_id=context.asterisk_id)
        except Exception as e:
            logger.error("Error while dialing endpoint %s : %s" %
                         (endpoint, e))
