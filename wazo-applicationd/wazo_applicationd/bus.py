# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
from asyncio import Queue
import asynqp  # type: ignore
from asynqp import IncomingMessage
from asynqp import Connection
from asynqp import channel
from asynqp import Exchange
from asynqp import Message
import logging
import json

from typing import Any
from typing import Callable
from typing import Dict
from typing import Awaitable

from wazo_appgateway_client import ApiClient  # type: ignore

from .config import Config
from .context import Context
from .models.application import Application
from .events import BaseEvent

SERVICE_ID = "wazo-applicationd"

logger = logging.getLogger(__name__)


class StasisEvent:

    asterisk_id: str
    application_uuid: str

    def __init__(self, asterisk_id: str, application_uuid: str) -> None:
        self.asterisk_id = asterisk_id
        self.application_uuid = application_uuid


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
    _stasis_event_cbs: Dict[str, Callable[[Context, StasisEvent, Any], Awaitable[None]]]
    _out_queue: Queue[BaseEvent]

    def __init__(self, config: Config, reconnect_rate: int = 1) -> None:
        self.config = config

        self._stasis_event_cbs = dict()
        self._out_queue = asyncio.Queue()

    async def run(self) -> None:
        logger.info("Start AMQP Bus")

        in_queue: Queue[IncomingMessage] = asyncio.Queue()
        self._out_queue = asyncio.Queue()

        await asyncio.gather(
            self._reconnector(in_queue, self._out_queue), self._consume_msgs(in_queue)
        )

    async def _consume(
        self, connection: Connection, queue: Queue[IncomingMessage]
    ) -> None:
        channel = await connection.open_channel()
        exchange = await channel.declare_exchange(
            self.config.get("amqp_exchange"), "topic"
        )

        amqp_queue = await channel.declare_queue(SERVICE_ID)

        # NOTE(safchain) need to find a better binding thing
        # so that not all application receive all messages
        await amqp_queue.bind(exchange, self.config.get("amqp_routing_key"))

        consumer = Consumer(queue)
        await amqp_queue.consume(consumer)

    async def _produce(self, connection: Connection, queue: Queue[BaseEvent]) -> None:
        channel = await connection.open_channel()

        # NOTE(safchain) exchange name part of the config file
        exchange = await channel.declare_exchange(SERVICE_ID, "topic")

        await self._produce_msgs(connection, exchange, queue)

    async def _reconnector(
        self, in_queue: Queue[IncomingMessage], _out_queue: Queue[BaseEvent]
    ) -> None:
        loop = asyncio.get_event_loop()
        try:
            connection = None
            while True:
                if connection is None or connection.is_closed():
                    logger.info("Connecting to rabbitmq...")
                    try:
                        connection = await asynqp.connect(
                            self.config.get("amqp_host"),
                            int(self.config.get("amqp_port")),
                            username=self.config.get("amqp_username"),
                            password=self.config.get("amqp_password"),
                        )

                        asyncio.gather(
                            self._consume(connection, in_queue),
                            self._produce(connection, _out_queue),
                        )
                    except asynqp.AMQPError as err:
                        logger.error("Connection error %s", err)
                        if connection is not None:
                            await connection.close()
                            connection = None
                    except (ConnectionError, OSError):
                        logger.error(
                            "Failed to connect to rabbitmq server. "
                            "Will retry in {} seconds".format(
                                self.config.get("amqp_reconnection_rate")
                            )
                        )
                        connection = None

                    if connection is None:
                        await asyncio.sleep(self.config.get("amqp_reconnection_rate"))
                    else:
                        logger.info("Successfully connected and consuming")

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()

    async def _consume_msgs(self, queue: Queue[IncomingMessage]) -> None:
        api = ApiClient()

        try:
            while True:
                queue_msg = await queue.get()
                queue_msg.ack()

                logger.debug(queue_msg.body)

                try:
                    obj = json.loads(queue_msg.body)
                except Exception as e:
                    logger.error("Error while decoding AMQP message: %s", e)
                    continue

                type = obj.get("type")
                if not type:
                    continue

                asterisk_id = obj.get("asterisk_id")
                if not asterisk_id:
                    logger.error("Error message without asterisk id: %s", queue_msg.body)
                    continue

                application_uuid = obj.get("application")
                if not Application.is_valid_uuid(application_uuid):
                    logger.error("Error not a valid application: %s", queue_msg.body)
                    continue

                msg = api.deserialize_obj(obj, "Message")
                cb = self._stasis_event_cbs.get(type)
                if cb:
                    context = Context(asterisk_id)
                    event = StasisEvent(asterisk_id, application_uuid)

                    await cb(context, event, msg)

        except asyncio.CancelledError:
            pass

    def _event_to_msg(self, event: BaseEvent) -> Message:
        return Message(event.body, headers=event.metadata)

    async def _produce_msgs(
        self, connection: Connection, exchange: Exchange, queue: Queue[BaseEvent]
    ) -> None:
        try:
            while True:
                event = await queue.get()
                msg = self._event_to_msg(event)
                logger.debug('Publishing event "%s": %s', event.name, msg)
                exchange.publish(msg, event.routing_key, mandatory=False)

        except asyncio.CancelledError:
            pass

    def publish(self, event: BaseEvent) -> None:
        self._out_queue.put_nowait(event)

    def on_event(
        self, type: str, cb: Callable[[Context, StasisEvent, Any], Awaitable[None]]
    ) -> None:
        self._stasis_event_cbs[type] = cb
