import logging
import swagger_client
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)

class ChannelMixin:

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