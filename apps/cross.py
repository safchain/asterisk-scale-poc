import asyncio
import logging
import json
from starlette.responses import Response
import argparse
import os
import errno
import hashlib
import os.path
import urllib.parse
import swagger_client
from swagger_client.rest import ApiException

from app import Application, Config

logger = logging.getLogger(__name__)


APP_NAME = "cross"


class BridgeApplication(Application):

    def __init__(self, config, id, name, register=False):
        super().__init__(config, id, name, register=register)

        self.master = None
        self.dials = set()

    async def on_start(self, context):
        logger.info(
            "Starting application on channel %s" % context)

        await self.get_or_create_bridge(context, "cross", "mixing")

        if not self.master:
            self.master = context.asterisk_id

        # answer to the call
        await self.answer(context)

    async def on_end(self, context):
        logger.info(
            "End of application on channel %s" % context)

    async def on_up(self, context):
        await self.bridge_add_channel(context, 'cross')

        if context.asterisk_id != self.master:
            if context.channel.id not in self.dials:
                channel = await self.dial(context, self.master, "7001")
                if channel:
                    self.dials.add(channel.id)

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

    app = BridgeApplication(config, args.id, APP_NAME,
                            register=args.register)
    app.launch()


if __name__ == "__main__":
    main()
