import asyncio
import asynqp
import logging
import aiohttp
import json

logging.basicConfig(level=logging.INFO)

RECONNECT_RATE = 1


class Consumer:

    def __init__(self, queue):
        self.queue = queue

    def __call__(self, msg):
        self.queue.put_nowait(msg)

    def on_error(self, exc):
        print("Connection lost while consuming queue", exc)


async def connect_and_consume(queue):
    connection = await asynqp.connect(
        'localhost', 5672, username='guest', password='guest')
    try:
        channel = await connection.open_channel()
        exchange = await channel.declare_exchange('wazo', 'topic')

        amqp_queue = await channel.declare_queue()
        await amqp_queue.bind(exchange, '#')

        consumer = Consumer(queue)
        await amqp_queue.consume(consumer)

    except asynqp.AMQPError as err:
        print("Could not consume on queue", err)
        await connection.close()
        return None
    return connection


async def reconnector(app, queue):
    try:
        connection = None
        while True:
            if connection is None or connection.is_closed():
                print("Connecting to rabbitmq...")
                try:
                    connection = await connect_and_consume(queue)
                except (ConnectionError, OSError):
                    print("Failed to connect to rabbitmq server. "
                          "Will retry in {} seconds".format(RECONNECT_RATE))
                    connection = None
                if connection is None:
                    await asyncio.sleep(RECONNECT_RATE)
                else:
                    print("Successfully connected and consuming")
                    await app.register()

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        if connection is not None:
            await connection.close()


async def process_msgs(app, queue):

    type_state_cb = {
        'StasisStart/Ring': app.onStart,
        'ChannelStateChange/Up': app.onUp,
        'StasisEnd/Up': app.onEnd
    }

    try:
        while True:
            msg = await queue.get()

            obj = json.loads(msg.body)

            asterisk_id = obj.get('asterisk_id', '')

            typ = obj.get('type', '')
            channel = Channel(obj.get('channel', {}))

            key = "%s/%s" % (typ, channel.state)

            callback = type_state_cb.get(key)
            if callback:
                # NOTE will be handled by a higher level component
                if channel.app_name == app.name:
                    await callback(asterisk_id, channel)

            msg.ack()
    except asyncio.CancelledError:
        pass


async def post(url, username, password):
    auth = aiohttp.BasicAuth(login=username, password=password)
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(url) as response:
            return response


class Channel:

    def __init__(self, obj):
        self.obj = obj

    @property
    def dialplan(self):
        return self.obj.get('dialplan', {})

    @property
    def app_name(self):
        dialplan = self.dialplan
        return dialplan.get('app_data')

    @property
    def id(self):
        return self.obj.get('id')

    @property
    def state(self):
        return self.obj.get('state')


class Application:

    def __init__(self, name):
        self.name = name

    async def register(self):
        print("Registering application %s" % self.name)

        # NOTE this will change in order to make a call toward consul
        response = await post("http://localhost:8888/ari/amqp/%s" % self.name,
                              "wazo", "wazo")
        if response.status <= 299:
            print("Application %s registered" % self.name)
        else:
            print("Error while registering application %s : %s" % (
                self.name, response.reason))


class HelloApplication(Application):

    def __init__(self, name):
        super().__init__("hello")

        self.hello_task = None

    async def onStart(self, asterisk_id, channel):
        print("Starting application on channel %s" % channel.id)
        asyncio.create_task(self.answer(asterisk_id, channel))

    async def onEnd(self, asterisk_id, channel):
        print("End of application on channel %s" % channel.id)

        if self.hello_task:
            self.hello_task.cancel()
            self.hello_task = None

    async def onUp(self, asterisk_id, channel):
        #self.hello_task = asyncio.create_task(
        #    self.say_hello(asterisk_id, channel))

        self.hello_task = asyncio.create_task(
            self.say_asterisk_id(asterisk_id, channel))

    async def request(self, asterisk_id, path):
        return await post("http://localhost:8888%s" % path, "wazo", "wazo")

    async def answer(self, asterisk_id, channel):
        print("Answering call on channel : %s" % channel.id)
        response = await self.request(asterisk_id, "/ari/channels/%s/answer" % channel.id)
        if response.status <= 299:
            print("Answered channel %s successful" % channel.id)
        else:
            print("Error while answering channel %s : %s" % (
                channel.id, response.reason))

    async def say_hello(self, asterisk_id, channel):
        while True:
            print("Going to say hello to channel %s" % channel.id)
            url = "/ari/channels/%s/play?media=sound:hello-world" % channel.id
            response = await self.request(asterisk_id, url)
            if response.status <= 299:
                print("Said hello on channel %s" % channel.id)
            else:
                print("Error while saiying hello %s : %s" % (
                    channel.id, response.reason))
            await asyncio.sleep(5)

    async def say_asterisk_id(self, asterisk_id, channel):
        while True:
            print("Going to say hello to channel %s" % channel.id)
            url = "/ari/channels/%s/play?media=sound:http://localhost:8000/hello-world.gsm" % channel.id
            response = await self.request(asterisk_id, url)
            if response.status <= 299:
                print("Said hello on channel %s" % channel.id)
            else:
                print("Error while saiying hello %s : %s" % (
                    channel.id, response.reason))
            await asyncio.sleep(5)

def main():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    app = HelloApplication("hello")

    reconnect_task = loop.create_task(reconnector(app, queue))
    process_msgs_task = loop.create_task(process_msgs(app, queue))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        process_msgs_task.cancel()
        reconnect_task.cancel()
        loop.run_until_complete(process_msgs_task)
        loop.run_until_complete(reconnect_task)
    loop.close()


if __name__ == "__main__":
    main()
