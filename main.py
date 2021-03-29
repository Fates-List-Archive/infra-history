from fastapi import FastAPI, Request, Form as FForm
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates
import asyncpg
from pydantic import BaseModel
import discord
import asyncio
from starlette_wtf import CSRFProtectMiddleware
import builtins
import importlib
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from modules.deps import *
from config import *
import orjson
import os
import aioredis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import logging
from fastapi.exceptions import HTTPException

#logging.basicConfig(level=logging.DEBUG)

# Setup Bots

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

intent_server = discord.Intents.default()
intent_server.typing = False
intent_server.bans = False
intent_server.emojis = False
intent_server.integrations = False
intent_server.webhooks = False
intent_server.invites = True
intent_server.voice_states = False
intent_server.messages = False
intent_server.members = True
intent_server.presences = False
builtins.client_servers = discord.Client(intents=intent_server)

limiter = FastAPILimiter
app = FastAPI(default_response_class = ORJSONResponse, docs_url = None, redoc_url = "/api/docs/endpoints")
app.add_middleware(SessionMiddleware, secret_key=session_key, https_only = True, max_age = 60*60*12, session_cookie = "fateslist_session_cookie") # 1 day expiry cookie

app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)
app.add_middleware(ProxyHeadersMiddleware)

@app.exception_handler(401)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
@app.exception_handler(500)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    return await FLError.error_handler(request, exc)

print("Loading discord modules for Fates List")
# Include all the modules
for f in os.listdir("modules/discord"):
    if not f.startswith("_") or f.startswith("."):
        path = "modules.discord." + f.replace(".py", "")
        print("Discord: Loading " + f.replace(".py", "") + " with path " + path)
        route = importlib.import_module(path)
        app.include_router(route.router)

print("All discord modules have loaded successfully!")

async def setup_db():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    # some table creation here meow
    return db

@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    print("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_servers.start(TOKEN_SERVER))
    await asyncio.sleep(4)
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    limiter.init(redis_db, identifier = rl_key_func)

@app.on_event("shutdown")
async def close():
    print("Closing")
    await redis_db.close()
    await redis_db.wait_closed()

@client.event
async def on_ready():
    print(client.user, "up")

@client_servers.event
async def on_ready():
    print(client_servers.user, "up [SERVER BOT]")


# Tag calculation
builtins.tags_fixed = []
for tag in TAGS.keys():
    tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": TAGS[tag], "id": tag})

builtins.server_tags_fixed = []
for tag in SERVER_TAGS.keys():
    server_tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": SERVER_TAGS[tag], "id": tag})

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    print(request.url)
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

def fl_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Fates List",
        version="1.0",
        description="Only v2 beta 1 API is supported (v1 is the old one fateslist.js currently uses)",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

#app.openapi = fl_openapi

