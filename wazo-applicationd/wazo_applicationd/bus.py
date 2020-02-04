# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Queue
import asynqp  # type: ignore
from asynqp import IncomingMessage
from asynqp import Connection
import logging
import json

from typing import Any
from typing import Callable
from typing import Dict
from typing import Awaitable

from openapi_client import ApiClient  # type: ignore

from .config import Config
from .context import Context
from .application import Application


SERVICE_ID = "applicationd"

logger = logging.getLogger(__name__)


class Event:

    asterisk_id: str
    application_name: str

    def __init__(self, asterisk_id: str, application_name: str) -> None:
        self.asterisk_id = asterisk_id
        self.application_name = application_name


class Consumer:

    queue: Queue[IncomingMessage]

    def __init__(self, queue: Queue[IncomingMessage]) -> None:
        self.queue = queue

    def __call__(self, msg: IncomingMessage) -> None:
        self.queue.put_nowait(msg)

    def on_error(self, exc: Exception) -> None:
        logger.error("Connection lost while consuming queue : {}".format(exc))


class Bus:

    config: Config
    event_cbs: Dict[str, Callable[[Context, Event, Any], Awaitable[None]]]

    def __init__(self, config: Config, reconnect_rate: int = 1) -> None:
        self.config = config

        self.event_cbs = dict()

    async def run(self) -> None:
        logger.info("start AMQP Bus")

        loop = asyncio.get_event_loop()
        queue: Queue[IncomingMessage] = asyncio.Queue()

        await asyncio.gather(
            self.reconnector(queue), self._process_msgs(queue)
        )

    async def connect_and_consume(
        self, queue: Queue[IncomingMessage]
    ) -> Connection:
        connection = await asynqp.connect(
            self.config.amqp_host,
            self.config.amqp_port,
            username=self.config.amqp_username,
            password=self.config.amqp_password,
        )

        try:
            channel = await connection.open_channel()
            exchange = await channel.declare_exchange(
                self.config.amqp_exchange, "topic"
            )

            amqp_queue = await channel.declare_queue(SERVICE_ID)

            # NOTE(safchain) need to find a better binding thing
            # so that not all application receive all messages
            await amqp_queue.bind(exchange, "#")

            consumer = Consumer(queue)
            await amqp_queue.consume(consumer)

        except asynqp.AMQPError as err:
            logger.error("Could not consume on queue {}".format(err))
            await connection.close()
            return None
        return connection

    async def reconnector(self, queue: Queue[IncomingMessage]) -> None:
        loop = asyncio.get_event_loop()
        try:
            connection = None
            while True:
                if connection is None or connection.is_closed():
                    logger.info("Connecting to rabbitmq...")
                    try:
                        connection = await self.connect_and_consume(queue)
                    except (ConnectionError, OSError):
                        logger.error(
                            "Failed to connect to rabbitmq server. "
                            "Will retry in {} seconds".format(
                                self.config.amqp_reconnection_rate
                            )
                        )
                        connection = None
                    if connection is None:
                        await asyncio.sleep(self.config.amqp_reconnection_rate)
                    else:
                        logger.info("Successfully connected and consuming")

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()

    async def _process_msgs(self, queue: Queue[IncomingMessage]) -> None:
        api = ApiClient()

        try:
            while True:
                queue_msg = await queue.get()
                queue_msg.ack()

                try:
                    obj = json.loads(queue_msg.body)
                except Exception as e:
                    logger.error(
                        "Error while decoding AMQP message: {}".format(e)
                    )
                    continue

                type = obj.get("type")
                if not type:
                    continue

                asterisk_id = obj.get("asterisk_id")
                if not asterisk_id:
                    logger.error(
                        "Error message without asterisk id: {}".format(obj)
                    )
                    continue

                application_name = obj.get("application")
                if not Application.is_valid(application_name):
                    logger.error(
                        "Error not a valid application: {}".format(
                            application_name
                        )
                    )
                    continue

                msg = api.deserialize_obj(obj, "Message")
                cb = self.event_cbs.get(type)
                if cb:
                    context = Context(asterisk_id)
                    event = Event(asterisk_id, application_name)

                    await cb(context, event, msg)

        except asyncio.CancelledError:
            pass

    def publish(self) -> None:
        pass

    def on_event(
        self, type: str, cb: Callable[[Context, Event, Any], Awaitable[None]]
    ) -> None:
        self.event_cbs[type] = cb
