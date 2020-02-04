import asyncio
import argparse
import logging
import signal
import sys

from wazo_applicationd.applicationd import Applicationd
from wazo_applicationd.config import Config

logger = logging.getLogger(__name__)

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",
                        help="local address that Asterisk can reach")
    parser.add_argument("--port",
                        type=int, help="local port that Asterisk can reach")
    parser.add_argument("--conf", default="",
                        help="application config file")
    args = parser.parse_args()

    config = Config()

    if args.conf:
        config.from_file(args.conf)

    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port

    await Applicationd(config).run()


if __name__ == "__main__":
    asyncio.run(main())
