from .imports import *
from .ratelimits import *
from discord import Client
from discord.ext.commands import Bot
    
class FatesDebug(Bot):
    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False
    
def setup_discord():
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
    client = Client(intents=intent_main)
    client.ready = False
    intent_server = deepcopy(intent_main)
    intent_server.presences = False
    client_server = Client(intents=intent_server)
    client_manager = FatesDebug(command_prefix = "fl!", intents=intents_server)
    return client, client_server, client_manager

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
def include_routers(app, fname, rootpath):
    for root, dirs, files in os.walk(rootpath):
        if not root.startswith("_") and not root.startswith(".") and not root.startswith("debug"):
            rrep = root.replace("/", ".")
            for f in files:
                if not f.startswith("_") and not f.startswith(".") and not f.endswith("pyc") and not f.startswith("models") and not f.startswith("base"):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)

                         
async def startup_tasks(app):
    """
    On startup:
        - Initialize the database
        - Get bot and server tags
        - Start the main and server bots using tokens in config_secrets.py
        - Sleep for 4 seconds to ensure connections are made before application startup
        - Setup Redis and initialize the ratelimiter and caching system
        - Connect robustly to rabbitmq for add bot/edit bot/delete bot
        - Start repeated task for vote reminder posting
        - Listen for broadcast events
    """
    builtins.up = False
    builtins.db = await setup_db()

    # Set bot tags
    def _tags(tag_db):
        tags =  {}
        for tag in tags_db:
            tags = tags | {tag["id"]: tag["icon"]}
        return tags
    
    tags_db = await db.fetch("SELECT id, icon FROM bot_list_tags")    
    tags = _tags(tags_db)
    builtins.TAGS = tags
    builtins.tags_fixed = calc_tags(tags)
    logger.info("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_servers.start(TOKEN_SERVER))
    builtins.redis_db = await aioredis.from_url('redis://localhost:12348', db = 1)
    workers = os.environ.get("WORKERS")
    asyncio.create_task(status(workers))
    await asyncio.sleep(4)
    app.add_middleware(SessionMiddleware, secret_key=session_key, https_only = True, max_age = 60*60*12, same_site = 'strict') # 1 day expiry cookie
    FastAPILimiter.init(redis_db, identifier = rl_key_func)
    builtins.rabbitmq_db = await aio_pika.connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.up = True
    await redis_db.publish(f"{instance_name}._worker", f"UP WORKER {os.getpid()} 0 {workers}") # Announce that we are up and not a repeat
    asyncio.create_task(start_dbg())
    await vote_reminder()

async def start_dbg():
    await asyncio.sleep(20) # Ensure all workers are up
    worker_ret = await add_rmq_task_with_ret("_worker", {})
    if worker_ret[1]:
        worker_lst = worker_ret[0]["ret"]
    else:
        worker_lst = []
    if worker_lst and worker_lst[0] == os.getpid():
        asyncio.create_task(client_dbg.start(TOKEN_MAIN))
    
async def status(workers):
    pubsub = redis_db.pubsub()
    await pubsub.subscribe(f"{instance_name}._worker")
    async for msg in pubsub.listen():
        if msg is None or type(msg.get("data")) != bytes:
            continue
        msg = msg.get("data").decode("utf-8").split(" ")
        match msg:
            case ["UP", "RMQ", _]:
                await redis_db.publish(f"{instance_name}._worker", f"UP WORKER {os.getpid()} 1 {workers}") # Announce that we are up and sending to repeat a message
            case ["REGET", "WORKER", reason]:
                logger.warning(f"RabbitMQ requesting REGET with reason {reason}")
                await redis_db.publish(f"{instance_name}._worker", f"UP WORKER {os.getpid()} 1 {workers}") # Announce that we are up and sending to repeat a message
            case _:
                pass # Ignore the rest for now

@repeat_every(seconds=60)
async def vote_reminder():
    reminders = await db.fetch("SELECT user_id, bot_id FROM user_reminders WHERE remind_time >= NOW() WHERE resolved = false")
    for reminder in reminders:
        logger.debug(f"Got reminder {reminder}")
        await bot_add_event(reminder["bot_id"], enums.APIEvents.vote_reminder, {"user": str(reminder["user_id"])})
        await db.execute("UPDATE user_reminders SET resolved = true WHERE user_id = $1 AND bot_id = $2", reminder["user_id"], reminder["bot_id"])
 
def calc_tags(TAGS):
    # Tag calculation
    tags_fixed = []
    for tag in TAGS.keys():
        # For every key in tag dict, create the "fixed" tag information (friendly and easy to use data for tags)
        tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": TAGS[tag], "id": tag})
    return tags_fixed

async def setup_db():
    """Function to setup the asyncpg connection pool"""
    db = await asyncpg.create_pool(host="localhost", port=12345, user=pg_user, database=f"fateslist_{instance_name}", password = pg_pwd)
    return db

def fl_openapi(app):
    def _openapi():
        """Custom OpenAPI description"""
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Fates List",
            version="1.0",
            description="Only v2 beta 3 API is supported (v1 is the old one that fateslist.js currently uses). The default API is v2. This means /api will point to this. To pin a api, either use the FL-API-Version header or directly use /api/v{version}.",
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    return _openapi
