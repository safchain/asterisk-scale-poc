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
import names

from app_sdk import Application, Config

logger = logging.getLogger(__name__)


APP_NAME = "astts"


class AsttsApplication(Application):

    def __init__(self, config, id, name, register=False,
                 data_dir='/tmp/astts'):
        super().__init__(config, id, name, register=register)

        self.data_dir = data_dir

        self.tts_tasks = dict()

        self.fastapi.get("/say")(self.say)

        self.nicknames = dict()

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
                tts = gTTS(text, lang='en')
                tts.write_to_fp(fp)

        proc = await asyncio.create_subprocess_exec(
            '/usr/bin/sox', fullpath, '-r', '8000', '-t', 'wav', '-',
            stdout=asyncio.subprocess.PIPE)

        data = await proc.stdout.read()

        await proc.wait()

        return Response(content=data, media_type="audio/wav")

    async def on_start(self, context):
        logger.info(
            "Starting application on channel %s" % context)

        nickname = self.nicknames.get(context.server_id)

        # generate nickname
        if not nickname:
            while True:
                nickname = names.get_first_name()
                if nickname not in self.nicknames.values():
                    self.nicknames[context.server_id] = nickname
                    break

        context.user_data = nickname

        await self.answer(context)

    async def on_end(self, context):
        logger.info(
            "End of application on channel %s" % context)

        task = self.tts_tasks.get(context)
        if task:
            task.cancel()
            self.tts_tasks.pop(context)

    async def on_up(self, context):
        task = asyncio.create_task(
            self.say_asterisk_id(context))
        self.tts_tasks[context] = task

    async def say_asterisk_id(self, context):
        while True:
            logger.info("Going to say something on channel %s" % context)

            nickname = context.user_data
            text = "Your are connected to Asterisk called %s" % nickname

            endpoint = "http://%s:%d" % (self.config.host, self.config.port)
            uri = "sound:%s/say?text=%s.wav" % (endpoint,
                                                urllib.parse.quote(text))

            await self.play_media(context, uri)

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
    parser.add_argument("--register", dest="register", default=False,
                        action='store_true',
                        help="application data directory")
    args = parser.parse_args()

    config = Config()

    if args.conf:
        config.from_conf(args.conf)

    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port

    app = AsttsApplication(config, args.id, APP_NAME,
                           data_dir=args.data_dir, register=args.register)
    app.launch()


if __name__ == "__main__":
    main()
