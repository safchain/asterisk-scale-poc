import asyncio
import logging
import json
from starlette.responses import Response
from gtts import gTTS
import argparse
import os
import errno
import hashlib
import os.path
import urllib.parse
import swagger_client
from swagger_client.rest import ApiException

from app import Application, Context

logger = logging.getLogger(__name__)


APP_NAME = "astts"


class AsttsApplication(Application):

    def __init__(self, context, id, name, data_dir='/tmp/astts'):
        super().__init__(context, id, name)

        self.data_dir = data_dir

        self.tts_tasks = dict()

        self.fastapi.get("/say")(self.say)

    async def say(self, text=""):
        text = text.rstrip('.wav')

        if not text:
            return

        try:
            os.makedirs(self.data_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        filename = hashlib.md5(text.encode()).hexdigest()
        fullpath = "%s/%s.mp3" % (self.data_dir, filename)

        if not os.path.isfile(fullpath):
            with open(fullpath, "wb") as fp:
                tts = gTTS(text, 'en')
                tts.write_to_fp(fp)

        proc = await asyncio.create_subprocess_exec(
            '/usr/bin/sox', fullpath, '-r', '8000', '-t', 'wav', '-',
            stdout=asyncio.subprocess.PIPE)

        data = await proc.stdout.read()

        await proc.wait()

        return Response(content=data, media_type="audio/wav")

    async def onStart(self, asterisk_id, channel):
        logging.info(
            "Starting application on channel %s:%s" %
            (asterisk_id, channel.id))
        await self.answer(asterisk_id, channel)

    async def onEnd(self, asterisk_id, channel):
        logging.info(
            "End of application on channel %s:%s" % (asterisk_id, channel.id))

        task = self.tts_tasks[channel.id]
        if task:
            task.cancel()
            self.tts_tasks.pop(channel.id)

    async def onUp(self, asterisk_id, channel):
        task = asyncio.create_task(
            self.say_asterisk_id(asterisk_id, channel))
        self.tts_tasks[channel.id] = task

    async def say_asterisk_id(self, asterisk_id, channel):
        while True:
            logging.info(
                "Going to say something on channel %s:%s" %
                (asterisk_id, channel.id))

            sub_id = asterisk_id.split(":")[-1]

            text = "Your are connected to Asterisk number %s" % sub_id

            endpoint = "http://%s:%d" % (self.context.host, self.context.port)
            uri = "sound:%s/say?text=%s.wav" % (endpoint,
                                                urllib.parse.quote(text))

            try:
                channels_api = swagger_client.ChannelsApi(self.api_client)
                await channels_api.channels_channel_id_play_post(
                    channel.id, [uri], x_asterisk_id=asterisk_id)

                logging.info("Said something on channel %s:%s" %
                             (asterisk_id, channel.id))
            except ApiException as e:
                logging.error("Error while saiying something %s : %s" % (
                    channel.id, e))
                return

            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id",
                        default=os.environ.get('ID', APP_NAME),
                        help="unique id for this app instance")
    parser.add_argument("--api-gateway",
                        default=os.environ.get('API', 'http://127.0.0.1:8888'),
                        help="http://<IP>:<Port>")
    parser.add_argument("--host",
                        help="local address that Asterisk can reach")
    parser.add_argument("--port",
                        type=int, help="local port that Asterisk can reach")
    parser.add_argument("--conf", default="",
                        help="application config file")
    parser.add_argument("--data-dir", default="/tmp/astts",
                        help="application data directory")
    args = parser.parse_args()

    context = Context()

    if args.conf:
        context.from_conf(args.conf)

    if args.host:
        context.host = args.host
    if args.port:
        context.port = args.port

    app = AsttsApplication(context, args.id, APP_NAME, args.data_dir)
    app.launch()


if __name__ == "__main__":
    main()
