import asyncio
import asynqp
import logging

logging.basicConfig(level=logging.INFO)

RECONNECT_BACKOFF = 1


class Consumer:

    def __init__(self, connection, queue):
        self.queue = queue
        self.connection = connection

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

        consumer = Consumer(connection, queue)
        await amqp_queue.consume(consumer)

    except asynqp.AMQPError as err:
        print("Could not consume on queue", err)
        await connection.close()
        return None
    return connection


async def reconnector(queue):
    try:
        connection = None
        while True:
            if connection is None or connection.is_closed():
                print("Connecting to rabbitmq...")
                try:
                    connection = await connect_and_consume(queue)
                except (ConnectionError, OSError):
                    print("Failed to connect to rabbitmq server. "
                          "Will retry in {} seconds".format(RECONNECT_BACKOFF))
                    connection = None
                if connection is None:
                    await asyncio.sleep(RECONNECT_BACKOFF)
                else:
                    print("Successfully connected and consuming")
            # poll connection state every 100ms
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        if connection is not None:
            await connection.close()


async def process_msgs(queue):
    try:
        while True:
            msg = await queue.get()
            print("Received", msg.body)
            msg.ack()
    except asyncio.CancelledError:
        pass


def main():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    # Start main indexing task in the background
    reconnect_task = loop.create_task(reconnector(queue))
    process_task = loop.create_task(process_msgs(queue))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        process_task.cancel()
        reconnect_task.cancel()
        loop.run_until_complete(process_task)
        loop.run_until_complete(reconnect_task)
    loop.close()


if __name__ == "__main__":
    main()
