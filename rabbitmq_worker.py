"""RabbitMQ worker"""
import asyncpg, asyncio, uvloop, aioredis
import sys
sys.path.append("..")
from config import *
from aio_pika import *
import discord
import orjson
import builtins
from copy import deepcopy
from termcolor import colored, cprint
from modules.utils import secure_strcmp
from modules.core import *
from rabbitmq.core import *

# Import all needed backends
backends = Backends()
builtins.backends = backends

# Setup main bot

intent_main = discord.Intents.default()
intent_main.typing = False
intent_main.bans = False
intent_main.emojis = False
intent_main.integrations = False
intent_main.webhooks = False
intent_main.invites = False
intent_main.voice_states = False
intent_main.messages = False
intent_main.members = True
intent_main.presences = True
builtins.client = discord.Client(intents=intent_main)

# Server bot

intent_server = deepcopy(intent_main)
intent_server.presences = False

builtins.client_server = discord.Client(intents=intent_server)

async def dbg_test():
    return "HELLO"

builtins.dbg_test = dbg_test

async def new_task(queue):
    friendly_name = backends.getname(queue)
    _channel = await rabbitmq_db.channel()
    _queue = await _channel.declare_queue(queue, durable = True) # Function to handle our queue
    
    async def _task(message: IncomingMessage):
        """RabbitMQ Queue Function"""
        curr = stats.on_message
        logger.opt(ansi = True).info(f"<m>{friendly_name} called (message {curr})</m>")
        stats.on_message += 1
        _json = orjson.loads(message.body)
        _headers = message.headers
        if not _headers:
            logger.error(f"Invalid auth for {friendly_name}")
            message.ack()
            return # No valid auth sent
        if not secure_strcmp(_headers.get("auth"), worker_key):
            logger.error(f"Invalid auth for {friendly_name} and JSON of {_json}")
            message.ack()
            return # No valid auth sent

        # Normally handle rabbitmq task
        _task_handler = TaskHandler(_json, queue)
        rc = await _task_handler.handle()
        if isinstance(rc, tuple):
            rc, err = rc[0], rc[1]
        else:
            err = False # Initially until we find exception

        _ret = {"ret": rc, "err": err} # Result to return
        if rc and isinstance(rc, Exception):
            logger.opt(ansi = True).warning(f"<red>{type(rc).__name__}: {rc}</red>")
            _ret["ret"] = [f"{type(rc).__name__}: {rc}"]
            if not _ret["err"]:
                _ret["err"] = [True] # Mark the error
            stats.err_msgs.append(message) # Mark the failed message so we can ack it later
        
        _ret["ret"] = _ret["ret"] if serialized(_ret["ret"]) else str(_ret["ret"])

        if _json["meta"].get("ret"):
            await redis_db.set(f"rabbit-{_json['meta'].get('ret')}", orjson.dumps(_ret)) # Save return code in redis

        if backends.ackall(queue) or not _ret["err"]: # If no errors recorded
            message.ack()
        logger.opt(ansi = True).info(f"<m>Message {curr} Handled</m>")
        await redis_db.incr("rmq_total_msgs", 1)
        stats.total_msgs += 1
        stats.handled += 1

    await _queue.consume(_task)

async def connect(start_time):
    """Main worker function"""
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER))
    builtins.rabbitmq_db = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    logger.opt(ansi = True).debug("Connected to databases (postgres, redis and rabbitmq)")
    builtins.stats = Stats()
    
    # Get handled message count
    stats.total_msgs = await redis_db.get("rmq_total_msgs")
    try:
        stats.total_msgs = int(stats.total_msgs)
    except:
        stats.total_msgs = 0

    channel = None
    while True: # Wait for discord.py before running tasks
        if channel is None:
            await asyncio.sleep(1)
            channel = client.get_channel(bot_logs)
        else:
            break
    for backend in backends.getall():
        await new_task(backend)
    end_time = time.time()
    stats.load_time = end_time - start_time
    logger.opt(ansi = True).info(f"<magenta>Worker up in {end_time - start_time} seconds at time {end_time}!</magenta>")

# TODO: Maybe move this to tasks.py with the rest of tasks later if this becomes too unmaintainable
class TaskHandler():
    def __init__(self, dict, queue):
        self.dict = dict
        self.ctx = dict["ctx"]
        self.meta = dict["meta"]
        self.queue = queue

    async def handle(self):
        try:
            handler = backends.get(self.queue)
            rc = await handler(self.dict, **self.ctx)
            return rc
        except Exception as exc:
            stats.errors += 1 # Record new error
            stats.exc.append(exc)
            return exc

class Stats():
    def __init__(self):
        self.errors = 0 # Amount of errors
        self.exc = [] # Exceptions
        self.err_msgs = [] # All messages that failed
        self.on_message = 1 # The currwnt message we are on. Default is 1
        self.handled = 0 # Handled messages count
        self.load_time = None # Amount of time taken to load site
        self.total_msgs = 0 # Total messages

    def cure(self, index):
        """'Cures' a error that has been handled"""
        self.errors -= 1
        del self.exc[index]
        del self.err_msgs[index]

    def __str__(self):
        s = []
        for k in self.__dict__.keys():
            s.append(f"{k}: {self.__dict__[k]}")
        return "\n".join(s)

# ENDTODO lines

# Run the task
if __name__ == "__main__":
    try:
        start_time = time.time()
        logger.opt(ansi = True).info(f"<magenta>Starting Fates List RabbitMQ Worker (time: {start_time})...</magenta>")
        backends.loadall() # Load all the backends
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(connect(start_time))
        #loop.create_task(connect(start_time))

        # we enter a never-ending loop that waits for data and runs
        # callbacks whenever necessary.
        loop.run_forever()
    except KeyboardInterrupt:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(rabbitmq.disconnect())
        except:
            pass
        logger.opt(ansi = True).info("<magenta>RabbitMQ worker down!</magenta>")
