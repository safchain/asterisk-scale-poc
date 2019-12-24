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

from app import Application, Context

logger = logging.getLogger(__name__)


class HelloApplication(Application):

    def __init__(self, context, id, name, data_dir='/tmp/astts'):
        super().__init__(context, id, "hello")

        self.data_dir = data_dir

        self.speak_task = None

        self.fastapi.get("/say")(self.say)

    async def say(self, text=""):
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
        asyncio.create_task(self.answer(asterisk_id, channel))

    async def onEnd(self, asterisk_id, channel):
        logging.info(
            "End of application on channel %s:%s" % (asterisk_id, channel.id))

        if self.speak_task:
            self.speak_task.cancel()
            self.speak_task = None

    async def onUp(self, asterisk_id, channel):
        self.speak_task = asyncio.create_task(
            self.say_asterisk_id(asterisk_id, channel))

    async def say_hello(self, asterisk_id, channel):
        while True:
            logging.info("Going to say hello to channel %s" % channel.id)
            url = "/ari/channels/%s/play?media=sound:hello-world" % channel.id
            response = await self.request(asterisk_id, url)
            if response.status <= 299:
                logging.info("Said hello on channel %s" % channel.id)
            else:
                logging.error("Error while saiying hello %s : %s" % (
                    channel.id, response.reason))
            await asyncio.sleep(5)

    async def say_asterisk_id(self, asterisk_id, channel):
        while True:
            logging.info(
                "Going to say something on channel %s:%s" %
                (asterisk_id, channel.id))

            sub_id = asterisk_id.split(":")[-1]

            endpoint = "http://%s:%d" % (self.context.addr, self.context.port)
            text = ('Your%2Bare%2Bconnected%2B'
                    'to%2BAsterisk%2Bnumber%2B' + sub_id)

            url = ("/ari/channels/%s/play?media=sound:"
                   "%s/say?text=%s") % (channel.id, endpoint, text)

            response = await self.request(asterisk_id, url)
            if response.status <= 299:
                logging.info(
                    "Said hello on channel %s:%s" %
                    (asterisk_id, channel.id))
            else:
                logging.error("Error while saiying hello %s : %s" % (
                    channel.id, response.reason))
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id",
                        help="unique id for this app instance")
    parser.add_argument("--api-gateway", default="http://localhost:8888",
                        help="http://<IP>:<Port>")
    parser.add_argument("--addr", default="127.0.0.1",
                        help="local address that Asterisk can reach")
    parser.add_argument("--port", default="8000", type=int,
                        help="local port that Asterisk can reach")
    parser.add_argument("--conf", default="",
                        help="application config file")
    parser.add_argument("--data-dir", default="/tmp/astts",
                        help="application data directory")
    args = parser.parse_args()

    context = Context()

    if args.conf:
        context.from_conf(args.conf)

    id = os.getenv("ID")
    if not id:
        id = args.id if args.id else "hello"

    if args.addr:
        context.addr = args.addr

    if args.port:
        context.port = args.port

    app = HelloApplication(context, id, "hello", args.data_dir)
    app.launch()


if __name__ == "__main__":
    main()
