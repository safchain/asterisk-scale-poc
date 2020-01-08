import logging
import swagger_client
from swagger_client.rest import ApiException

logger = logging.getLogger(__name__)

class MediaMixin:

    def __init__(self, *args, **kwargs):
        super(MediaMixin, self).__init__()

    async def play_media(self, context, uri):
        if context not in self.contextes:
            return

        try:
            channels_api = swagger_client.ChannelsApi(self.api_client)
            await channels_api.channels_channel_id_play_post(
                context.channel.id, [uri], x_asterisk_id=context.asterisk_id)

            logger.info("Play something on channel %s" % context)
        except ApiException as e:
            logger.error("Error while playing something %s : %s" %
                         (context, e))