import aiohttp
from aiohttp import web
import asyncio
import asynqp
import logging
import json
import yaml
import consul.aio
import os
import uvicorn
from fastapi import FastAPI
import swagger_client
from swagger_client import Configuration
from swagger_client.rest import ApiException

RECONNECT_RATE = 1

logger = logging.getLogger(__name__)


class Config:

    def __init__(self):
        self.host = os.environ.get('APP_HOST', '127.0.0.1')
        self.port = int(os.environ.get('APP_PORT', '8000'))

        self.api_endpoint = os.environ.get('API_ENDPOINT',
                                           'http://localhost:8088')
        self.api_username = os.environ.get('API_USERNAME', 'wazo')
        self.api_password = os.environ.get('API_PASSWORD', 'wazo')

        self.amqp_host = os.environ.get('AMQP_HOST', '127.0.0.1')
        self.amqp_port = int(os.environ.get('AMQP_PORT', '5672'))
        self.amqp_username = os.environ.get('AMQP_USERNAME', 'guest')
        self.amqp_password = os.environ.get('AMQP_PASSWORD', 'guest')
        self.amqp_exchange = os.environ.get('AMQP_EXCHANGE', 'wazo')

        self.consul_host = os.environ.get('CONSUL_HOST', '127.0.0.1')
        self.consul_port = int(os.environ.get('CONSUL_PORT', '8500'))

    def from_conf(self, conf="app.yml"):
        doc = {}
        if os.path.isfile(conf):
            with open(conf) as f:
                doc = yaml.load(f, Loader=yaml.FullLoader)

        self.host = doc.get('address', self.host)
        self.port = doc.get('port', self.port)

        api = doc.get('api')
        if api:
            self.api_endpoint = api.get('endpoint')
            self.api_username = api.get('username')
            self.api_password = api.get('password')

        amqp = doc.get('amqp')
        if amqp:
            self.amqp_host = amqp.get('host')
            self.amqp_port = amqp.get('port')
            self.amqp_username = amqp.get('username')
            self.amqp_password = amqp.get('password')
            self.amqp_exchange = amqp.get('exchange')

        consul = doc.get('consul')
        if consul:
            self.consul_host = consul.get('host')
            self.consul_port = consul.get('port')


class Context:

    def __init__(self, asterisk_id, channel):
        self.asterisk_id = asterisk_id
        self.channel = channel
        self._user_data = None

    def __hash__(self):
        return hash((self.asterisk_id, self.channel.id))

    def __eq__(self, other):
        return ((self.asterisk_id, self.channel.id) ==
                (other.asterisk_id, other.channel.id))

    def __ne__(self, other):
        return not(self == other)

    def get_user_data(self):
        return self._user_data

    def set_user_data(self, user_data):
        self._user_data = user_data

    def del_user_data(self):
        self._user_data = None

    user_data = property(get_user_data, set_user_data, del_user_data)

    def __str__(self):
        return "%s/%s" % (self.asterisk_id, self.channel.id)

    def __repr__(self):
        return "%s/%s" % (self.asterisk_id, self.channel.id)

    @property
    def server_id(self):
        return self.asterisk_id

class Channel:

    def __init__(self, obj):
        self.obj = obj

    @property
    def dialplan(self):
        return self.obj.get('dialplan', {})

    @property
    def id(self):
        return self.obj.get('id')

    @property
    def state(self):
        return self.obj.get('state')


class Consumer:

    def __init__(self, queue):
        self.queue = queue

    def __call__(self, msg):
        self.queue.put_nowait(msg)

    def on_error(self, exc):
        logger.error("Connection lost while consuming queue : %s" % exc)


class Application:

    def __init__(self, config, id, name, register=False):
        self.config = config
        self.id = id
        self.name = name
        self.register = register

        self.fastapi = FastAPI()

        self.contextes = dict()

        configuration = Configuration()
        configuration.host = "%s/ari" % config.api_endpoint
        configuration.username = config.api_username
        configuration.password = config.api_password

        self.api_client = swagger_client.ApiClient(configuration)

    def launch(self):
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        reconnect_task = loop.create_task(self.reconnector(loop, queue))
        process_msgs_task = loop.create_task(
            self.process_msgs(queue))

        # mainly for dev or debug purpose when not using consul
        if self.register:
            ari_register_task = loop.create_task(self.register_all_ari(loop))

        api_task = loop.create_task(self.run_api())
        register_task = loop.create_task(self.register_consul(loop))

        try:
            loop.run_until_complete(api_task)
        finally:
            register_task.cancel()

            if self.register:
                ari_register_task.cancel()

            reconnect_task.cancel()
            process_msgs_task.cancel()

            loop.run_until_complete(register_task)

            if self.register:
                loop.run_until_complete(ari_register_task)

            loop.run_until_complete(reconnect_task)
            loop.run_until_complete(process_msgs_task)

            loop.close()

    async def run_api(self):
        try:
            self.fastapi.get("/status")(self.status)

            config = uvicorn.Config(self.fastapi,
                                    host="0.0.0.0", port=self.config.port)

            server = uvicorn.Server(config)

            await server.serve()
        except asyncio.CancelledError:
            pass

    async def status(self):
        return {'state': 'ok'}

    async def connect_and_consume(self, queue):
        connection = await asynqp.connect(
            self.config.amqp_host, self.config.amqp_port,
            username=self.config.amqp_username,
            password=self.config.amqp_password)
        try:
            channel = await connection.open_channel()
            exchange = await channel.declare_exchange(
                self.config.amqp_exchange, 'topic')

            amqp_queue = await channel.declare_queue('apps')
            await amqp_queue.bind(exchange, '#')

            consumer = Consumer(queue)
            await amqp_queue.consume(consumer)

        except asynqp.AMQPError as err:
            logger.error("Could not consume on queue %s" % err)
            await connection.close()
            return None
        return connection

    async def reconnector(self, loop, queue):
        try:
            connection = None
            while True:
                if connection is None or connection.is_closed():
                    logger.info("Connecting to rabbitmq...")
                    try:
                        connection = await self.connect_and_consume(queue)
                    except (ConnectionError, OSError):
                        logger.error("Failed to connect to rabbitmq server. "
                                     "Will retry in {} seconds".format(RECONNECT_RATE))
                        connection = None
                    if connection is None:
                        await asyncio.sleep(RECONNECT_RATE)
                    else:
                        logger.info("Successfully connected and consuming")

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            if connection is not None:
                await connection.close()

    async def process_msgs(self, queue):

        type_state_cb = {
            'StasisStart/Ring': self.on_start,
            'ChannelStateChange/Up': self.on_up,
            'StasisEnd/Up': self.on_end
        }

        try:
            while True:
                msg = await queue.get()

                try:
                    obj = json.loads(msg.body)
                except Exception as e:
                    logger.error("Error while decoding AMQP message: %s" % e)
                    continue

                asterisk_id = obj.get('asterisk_id', '')

                typ = obj.get('type', '')
                app = obj.get('application', '')
                if app != self.name:
                    continue

                channel = Channel(obj.get('channel', {}))
                key = "%s/%s" % (typ, channel.state)

                context = Context(asterisk_id, channel)
                context = self.contextes.get(context, context)

                if typ == "StasisStart":
                    self.contextes[context] = context
                elif typ == "StasisEnd":
                    self.contextes.pop(context)

                callback = type_state_cb.get(key)
                if callback:
                    await callback(context)

                msg.ack()
        except asyncio.CancelledError:
            pass

    async def register_consul(self, loop):
        app_registered = False
        try:
            c = consul.aio.Consul(
                host=self.config.consul_host,
                port=self.config.consul_port, loop=loop)

            revision = 1
            while True:
                try:
                    logger.info(
                        "Registering application %s in Consul" % self.name)
                    if not app_registered:
                        response = await c.kv.put("applications/%s" % self.name,
                                                  "%d" % revision)
                        if response is not True:
                            raise Exception(
                                "error",
                                "registering application %s" % self.name)
                        app_registered = True

                    service_id = "apps/%s" % self.id
                    service_name = self.name

                    response = await c.agent.service.register(
                        service_name, service_id=service_id,
                        address=self.config.host, port=self.config.port,
                    )
                    if response is not True:
                        raise Exception("error",
                                        "registering service %s" % self.name)

                    status_url = "http://%s:%d/status" % (
                        self.config.host, self.config.port)
                    response = await c.agent.check.register(
                        self.name, consul.Check.http(status_url, '5s'),
                        service_id=service_id)
                    if response is not True:
                        raise Exception("error",
                                        "registering check %s" % self.name)

                    logger.info(
                        "Service check %s registered in Consul" % self.name)

                    revision += 1
                except Exception as e:
                    logger.error("Consul error: %s", e)

                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def register_all_ari(self, loop):
        try:
            c = consul.aio.Consul(
                host=self.config.consul_host,
                port=self.config.consul_port, loop=loop)

            while True:
                eids = []

                (_, nodes) = await c.health.service("asterisk")
                for node in nodes:
                    service = node.get("Service", {})
                    meta = service.get("Meta", {})
                    eid = meta.get("eid")

                    if eid:
                        eids.append(eid)

                for eid in eids:
                    await self.register_ari(eid)

                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def register_ari(self, asterisk_id):
        while True:
            # NOTE this will change in order to make a call toward consul
            if asterisk_id:
                logger.info(
                    "Registering application %s on %s" %
                    (self.name, asterisk_id))
            else:
                logger.info("Registering application %s" % self.name)

            try:
                amqp_api = swagger_client.AmqpApi(self.api_client)
                await amqp_api.amqp_app_name_post(
                    self.name, x_asterisk_id=asterisk_id)

                logger.info("Registered application %s" % self.name)
            except Exception as e:
                logger.error("Error while registering application %s : %s" % (
                    self.name, e))

            await asyncio.sleep(5)

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
            return

    def run(self):
        pass

    async def on_start(self, context):
        pass

    async def on_end(self, context):
        pass

    async def on_up(self, context):
        pass
