import asyncio
import logging
import json
import uvicorn
from fastapi import FastAPI
from starlette.responses import Response
import tempfile
from gtts import gTTS
import argparse

from app import Application, Context

logger = logging.getLogger(__name__)

class HelloApplication(Application):

    def __init__(self, context, name, addr, port=8080):
        super().__init__(context, "hello")

        self.addr = addr
        self.port = port

        self.speak_task = None

    async def run(self):
        try:
            app = FastAPI()

            app.get("/say")(self.say)

            config = uvicorn.Config(app, host=self.addr, port=self.port)
            server = uvicorn.Server(config)

            await server.serve()
        except asyncio.CancelledError:
            pass

    async def say(self, text=""):
        fp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts = gTTS(text, 'en')
        tts.write_to_fp(fp)
        fp.close()

        proc = await asyncio.create_subprocess_exec(
            '/usr/bin/sox', fp.name, '-r', '8000', '-t', 'wav', '-',
            stdout=asyncio.subprocess.PIPE)

        data = await proc.stdout.read()

        await proc.wait()

        return Response(content=data, media_type="audio/wav")

    async def onStart(self, asterisk_id, channel):
        logging.info("Starting application on channel %s" % channel.id)
        asyncio.create_task(self.answer(asterisk_id, channel))

    async def onEnd(self, asterisk_id, channel):
        logging.info("End of application on channel %s" % channel.id)

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
            logging.info("Going to say hello to channel %s" % channel.id)

            endpoint = "http://%s:%d" % (self.addr, self.port)
            text = 'Your%2Bare%2Bconnected%2Bto%2BAsterisk%2Bnumber%2B' + asterisk_id

            url = ("/ari/channels/%s/play?media=sound:"
                   "%s/say?text=%s") % (channel.id, endpoint, text)

            response = await self.request(asterisk_id, url)
            if response.status <= 299:
                logging.info("Said hello on channel %s" % channel.id)
            else:
                logging.error("Error while saiying hello %s : %s" % (
                    channel.id, response.reason))
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-gateway", default="http://localhost:8888",
                        help="http://<IP>:<Port>")
    parser.add_argument("--addr", default="127.0.0.1",
                        help="local address that Asterisk can reach")
    parser.add_argument("--port", default="8000", type=int,
                        help="local port that Asterisk can reach")
    parser.add_argument("--conf", default="",
                        help="application config file")
    args = parser.parse_args()

    context = Context()

    if args.conf:
        context.from_conf(conf)

    app = HelloApplication(context, "hello", args.addr, args.port)
    app.launch()


if __name__ == "__main__":
    main()
