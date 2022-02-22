#pylint: disable=E1101,W0212
"""Fates List System Bootstrapper"""
import asyncio
import builtins
import datetime
import importlib
import os
import signal
import sys
import time
import uuid
from http import HTTPStatus

import aioredis
import asyncpg
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import (HTTPException, RequestValidationError,
                                ValidationError)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi_cprofile.profiler import CProfileMiddleware
from fastapi.routing import APIRoute
from lynxfall.core.classes import Singleton
from lynxfall.oauth.models import OauthConfig
from lynxfall.oauth.providers.discord import DiscordOauth
from lynxfall.ratelimits import LynxfallLimiter
from lynxfall.utils.fastapi import api_versioner, include_routers
from lynxfall.utils.string import get_token, secure_strcmp
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from config import (API_VERSION, discord_client_id, discord_client_secret,
                    discord_redirect_uri, sentry_dsn, site, session_key,
                    rl_key)
from config._logger import logger
from modules.core.ipc import redis_ipc_new
from modules.models import enums
from itsdangerous import URLSafeSerializer

sys.pycache_prefix = "data/pycache"
reboot_error = "<h1>Fates List is currently rebooting. Please click <a href='/maint/page'>here</a> for more information</h1>"

class FatesListRequestHandler(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Request Handler for Fates List"""
    def __init__(self, app):
        super().__init__(app)
        
        # Methods that should be allowed by CORS
        self.cors_allowed = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
            
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        if request.headers.get("method"):
            request.scope["method"] = request.headers.get("method", "GET")
        request.state.error_id = str(uuid.uuid4())
        request.state.curr_time = str(datetime.datetime.now())

        if not request.scope["path"].startswith("/api"):
            request.scope["path"] = request.scope["path"].replace("/", "/api/v2/", 1)

        path = request.scope["path"]
        
        if not request.app.state.worker_session.up:
            # Still accept connections but be warned that connections may stall indefinitely
            logger.warning("Accepting bad connection without working IPC")
            #return HTMLResponse(reboot_error + f"<br>Worker UP: {request.app.state.worker_session.up}")

        res = await self._dispatcher(path, request, call_next)

        return res if res else self.default_res
    
    async def _dispatcher(self, path, request, call_next):
        """Actual middleware"""
        if request.app.state.worker_session.dying:
            return HTMLResponse("Fates List is going down for a reboot")
       
        request.scope["session"] = {}

        logger.trace(request.headers.get("X-Forwarded-For"))
        
        # These are checks path should not start with
        is_api = path.startswith("/api")

        if path.startswith("/bots/"):
            path = path.replace("/bots", "/bot", 1)
        
        request.scope["path"] = path
        
        if is_api:
            # Handle /api as /api/vX excluding docs + pinned requests
            request.scope, api_ver = api_versioner(request, API_VERSION)
    
        start_time = time.time()
        
        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Worker-PID"] = str(os.getpid())
        response.headers["Content-Security-Policy"] = "default-src 'none'; connect-src 'self' https://discord.com https://fateslist.xyz; script-src https: 'unsafe-inline'; img-src https: data:; font-src https: data:; child-src https: blob:; style-src https: 'unsafe-inline'; object-src 'none'; frame-ancestors https://fateslist.xyz https://sunbeam.fateslist.xyz https://docs.fateslist.xyz https://apidocs.fateslist.xyz; base-uri 'none'; report-uri /api/v2/_csp"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
    
        # Fuck CORS by force setting headers with proper origin
        origin = request.headers.get('Origin')

        # Make commonly repepated headers shorter
        acac = "Access-Control-Allow-Credentials"
        acao = "Access-Control-Allow-Origin"
        acam = "Access-Control-Allow-Methods"

        response.headers[acao] = origin if origin else "*"
        response.headers["Access-Control-Allow-Headers"] = "Frostpaw, Frostpaw-Server, Content-Type, Set-Cookie, Frostpaw-Auth, Frostpaw-Vote-Page, Authorization, Method"
        
        if is_api and origin or origin in ("https://sunbeam.fateslist.xyz", "https://fateslist.xyz"):
            response.headers[acac] = "true"
        else:
            response.headers[acac] = "false"
        
        response.headers[acam] = self.cors_allowed
        if response.status_code in (404, 405):
            if request.method == "OPTIONS" and is_api:
                response.status_code = 200
                response.headers["Allow"] = self.cors_allowed
       
        return response if response else PlainTextResponse("Something went wrong!")
        
class FatesWorkerOauth(Singleton):  # pylint: disable=too-few-public-methods
    """Stores all oauths (currently only discord)"""
    
    def __init__(
        self,
        *,
        discord_oauth: DiscordOauth
    ):
        self.discord = discord_oauth

class FatesWorkerSession(Singleton):  # pylint: disable=too-many-instance-attributes
    """Stores a worker session"""

    def __init__(
        self,
        *, 
        app: FastAPI,
        session_id: str,
        postgres: asyncpg.Pool,
        redis: aioredis.Connection,
        oauth: FatesWorkerOauth,
        worker_count: int
    ):
        self.id = session_id
        self.postgres = postgres
        self.redis = redis
        self.oauth = oauth
        self.worker_count = worker_count
        self.tags = {}
        self.tags_fixed = []
        self.app = app

        # Record basic stats and initially set workers to None
        self.start_time = time.time()
        self.up = False
        self.workers = []
        
        # FUP = finally up/all workers are now up
        self.fup = False
        
        # Used in shutdown to check if already dead
        self.dying = False
        
    def publish_workers(self, workers):
        """Publish workers"""
        self.workers = workers
        self.workers.sort()
        self.fup = True

    def primary_worker(self):
        """Returns if we are primary (first) worker"""
        return self.fup and self.workers[0] == os.getpid()

    def get_worker_index(self):
        """
        This function should only be called 
        after workers are published
        """
        return self.workers.index(os.getpid())

def fix_operation_ids(app) -> None:
    """
    Simplify operation IDs so that generated API docs are easier to link to.
    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            if not route.operation_id or "__" in route.operation_id:
                route.operation_id = route.name  # in this case, 'read_items'

async def init_fates_worker(app, session_id, workers):
    """
    On startup:
        - Initialize Postgres andRedis
        - Setup the ratelimiter and IPC worker protocols
        - Start repeated task for vote reminder posting
    """
    builtins.app = app
    # Add request handler
    app.add_middleware(
        FatesListRequestHandler, 
    )

    if os.environ.get("PROFILE"):
        app.add_middleware(CProfileMiddleware, enable=True, server_app=app, filename="flprofile.pstats", strip_dirs=False, sort_by='cumulative')
        app.state.cprof = app.user_middleware[0]

    dbs = await setup_db()

    # Wait for redis ipc to come up
    app.state.first_run = True

    async def wait_for_ipc(first_run: bool = False):
        logger.info("Wait for ipc called")
        ipc_up = False
        if not first_run:
            app.state.worker_session.up = False

        while not ipc_up:
            resp = await redis_ipc_new(dbs["redis"], "PING", timeout=5)
            logger.info(resp)
            if not resp:
                invalid = True
                reason = "IPC not up"
            else:
                resp1 = resp.decode("utf-8")
                invalid, reason = False, "All good!"
                respl = resp1.split(" ")
                if len(respl) != 3:
                    invalid, reason = True, "Invalid PONG payload"
                if respl[0] != "PONG":
                    invalid, reason = True, "IPC corrupt"
                if respl[1] != "V3":
                    invalid, reason = True, f"Invalid IPC version: {respl[1]}"

                if not invalid:
                    app.state.site_degraded = (respl[2] == "1")
        
            if invalid:  # pylint: disable=no-else-continue
                logger.info(f"Invalid IPC. Got invalid PONG: {resp} (reason: {reason})")
                continue

            if first_run:
                return await finish_init(app, session_id, workers, dbs)
            app.state.worker_session.up = True
            return

    app.state.wait_for_ipc = wait_for_ipc
    await app.state.wait_for_ipc(first_run=True)

async def finish_init(app, session_id, workers, dbs):
    """Finish site init"""
    logger.success("Connected to postgres and redis")

    app.state.worker_session = FatesWorkerSession(
        app=app,
        session_id=session_id,
        postgres=dbs["postgres"],
        redis=dbs["redis"],
        oauth=FatesWorkerOauth(
            discord_oauth=DiscordOauth(
                oc=OauthConfig(
                    client_id=discord_client_id,
                    client_secret=discord_client_secret,
                    redirect_uri=discord_redirect_uri
                ),
            )
        ),
        worker_count=workers
    )

    # Set the session for use in startup
    session = app.state.worker_session
   
    app.state.rl_key = rl_key

    # Set bot tags
    def _tags(tag_db):
        tags = {}
        for tag in tag_db:
            tags = tags | {tag["id"]: tag["icon"]}
        return tags

    tags_db = await session.postgres.fetch(
        "SELECT id, icon FROM bot_list_tags"
    )
    tags = _tags(tags_db)
    builtins.TAGS = tags # TODO: Remove this
    app.state.worker_session.tags = tags
    builtins.tags_fixed = calc_tags(tags)
    app.state.worker_session.tags_fixed = calc_tags(tags)

    # Setup sentry
    sentry_sdk.init(sentry_dsn)  # pylint: disable=abstract-class-instantiated
    app.add_middleware(SentryAsgiMiddleware)

    # Setup ratelimiter
    LynxfallLimiter.init(session.redis, identifier=rl_key_func)
        
    # Include all routers
    include_routers(app, "Discord", "modules/discord")

    # Fix operation ids
    fix_operation_ids(app)

    logger.success(
        f"Fates List worker (pid: {os.getpid()}) bootstrapped successfully!"
    )

# IP Checker
def ip_check(request: Request) -> str:
    """Given a request, try to find its IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        logger.trace(f"Forwarded IPs are {forwarded}")
        return forwarded.split(",")[0]
    return request.client.host

async def rl_key_func(request: Request) -> str:
    """Ratelimit identifier function"""
    db = request.app.state.worker_session.postgres

    if os.environ.get("ALLOW_RL_BYPASS") and secure_strcmp(str(request.headers.get("X-RL-Bypass")), request.app.state.rl_key):
        return None
    
    if ("Authorization" in request.headers or "authorization" in request.headers):
        r = request.headers.get("Authorization") or request.headers.get("authorization")
        check = await db.fetchrow("SELECT bot_id, state FROM bots WHERE api_token = $1", r) # Check api token
        if check is None:
            # Check user token too
            check_user = await db.fetchval("SELECT user_id FROM users WHERE api_token = $1", r) # Check api token
            if check_user is None:
                return ip_check(request) # Invalid api token, fallback to ip
            return str(check_user)
        if check["state"] == enums.BotState.certified:
            return None
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    return ip_check(request) # Fallback to ip


# Tags
def calc_tags(list_tags):
    """Calculate bot list tags"""
    # Tag calculation
    tags_fixed = []
    for tag in list_tags.keys():
        # For every key in tag dict, 
        # create the "fixed" tag information 
        # (friendly and easy to use data for tags)
        tags_fixed.append({
            "name": tag.replace("_", " ").title(),
            "iconify_data": list_tags[tag], 
            "id": tag
        })
    return tags_fixed


async def setup_db():
    """Function to setup the asyncpg connection pool"""
    postgres = await asyncpg.create_pool()
    redis = await aioredis.from_url('redis://localhost:1001', db=1)
    return {"postgres": postgres, "redis": redis}
