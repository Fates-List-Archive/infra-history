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
from fastapi.exceptions import (HTTPException, RequestValidationError,
                                ValidationError)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_cprofile.profiler import CProfileMiddleware
from fastapi.routing import APIRoute
from lynxfall.core.classes import Singleton
from lynxfall.oauth.models import OauthConfig
from lynxfall.oauth.providers.discord import DiscordOauth
from lynxfall.ratelimits import LynxfallLimiter
from lynxfall.utils.fastapi import api_versioner, include_routers
from lynxfall.utils.string import get_token
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import (API_VERSION, discord_client_id, discord_client_secret,
                    discord_redirect_uri, sentry_dsn, site)
from config._logger import logger
from modules.core.error import WebError
from modules.core.ipc import redis_ipc_new
from modules.core.ratelimits import rl_key_func
from modules.models import enums

sys.pycache_prefix = "data/pycache"
reboot_error = "<h1>Fates List is currently rebooting. Please click <a href='/maint/page'>here</a> for more information</h1>"

class FatesListRequestHandler(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Request Handler for Fates List"""
    def __init__(self, app, *, exc_handler):
        super().__init__(app)
        self.exc_handler = exc_handler
        app.add_exception_handler(Exception, exc_handler)
        
        # Methods that should be allowed by CORS
        self.cors_allowed = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
    
    @staticmethod
    def _log_req(path, request, response):
        """Logs HTTP requests to console (and file)"""
        code = response.status_code
        phrase = HTTPStatus(response.status_code).phrase
        query_str_raw = request.scope["query_string"]

        if query_str_raw:
            query_str = f'?{query_str_raw.decode("utf-8")}'
        else:
            query_str = ""
            
        logger.info(
            f"{request.method} {path}{query_str} | {code} {phrase}"
        )
        
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        request.state.error_id = str(uuid.uuid4())
        request.state.curr_time = str(datetime.datetime.now())
        path = request.scope["path"]
        
        if not request.app.state.worker_session.up:
            # Still accept connections but be warned that connections may stall indefinitely
            logger.warning("Accepting bad connection without working IPC")
            #return HTMLResponse(reboot_error + f"<br>Worker UP: {request.app.state.worker_session.up}")

        try:
            res = await self._dispatcher(path, request, call_next)
        except:  # pylint: disable=broad-except
            exc = sys.exc_info()[2]
            res = await self.exc_handler(request, exc, log=True)
        
        try:
            self._log_req(path, request, res)
        except:  # pylint: disable=bare-except
            pass
        return res if res else self.default_res
    
    async def _dispatcher(self, path, request, call_next):
        """Actual middleware"""
        if request.app.state.worker_session.dying:
            return HTMLResponse("Fates List is going down for a reboot")
        
        logger.trace(request.headers.get("X-Forwarded-For"))
        
        if path.startswith("/bots/"):
            path = path.replace("/bots", "/bot", 1)
        
        # These are checks path should not start with
        is_api = path.startswith("/api")
        request.scope["path"] = path
        
        if is_api:
            # Handle /api as /api/vX excluding docs + pinned requests
            request.scope, api_ver = api_versioner(request, API_VERSION)
    
        start_time = time.time()
        
        # Process request with retry
        try:
            response = await call_next(request)
        except:  # pylint: disable=broad-except
            err = sys.exc_info()
            try:
                response = await self.exc_handler(request, err[2])
            except:
                response = PlainTextResponse(err[1])

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Worker-PID"] = str(os.getpid())
        response.headers["Content-Security-Policy"] = "default-src 'none'; connect-src 'self' https://discord.com https://fateslist.xyz; script-src https: 'unsafe-inline'; img-src https: data:; font-src https: data:; child-src https: blob:; style-src https: 'unsafe-inline'; object-src 'none'; frame-ancestors https://docs.fateslist.xyz https://apidocs.fateslist.xyz; base-uri 'none'; report-uri /fates/csp"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"

        if is_api:
            response.headers["X-API-Version"] = api_ver
    
        # Fuck CORS by force setting headers with proper origin
        origin = request.headers.get('Origin')

        # Make commonly repepated headers shorter
        acac = "Access-Control-Allow-Credentials"
        acao = "Access-Control-Allow-Origin"
        acam = "Access-Control-Allow-Methods"

        response.headers[acao] = origin if origin else "*"
        response.headers["Access-Control-Allow-Headers"] = "Frostpaw, Frostpaw-Server, Content-Type, Set-Cookie"
        
        if is_api and origin:
            response.headers[acac] = "true"
        else:
            response.headers[acac] = "false"
        
        response.headers[acam] = self.cors_allowed
        if response.status_code == 405:
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

        # Record basic stats and initially set workers to None
        self.start_time = time.time()
        self.up = False
        self.workers = []
        
        # FUP = finally up/all workers are now up
        self.fup = False
        
        # Used in shutdown to check if already dead
        self.dying = False
        
        # Templating
        self.templates = Jinja2Templates(directory="data/templates")

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
        exc_handler=WebError.error_handler,
    )

    if os.environ.get("PROFILE"):
        app.add_middleware(CProfileMiddleware, enable=True, server_app=app, filename="flprofile.pstats", strip_dirs=False, sort_by='cumulative')
        app.state.cprof = app.user_middleware[0]
    # This is still builtins for backward compatibility. 
    # ========================================================
    # Move all code to use worker session. All new code should 
    # always use worker session instead of builtins
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
            
            else:
                app.state.worker_session.up = True
                return

    app.state.wait_for_ipc = wait_for_ipc
    await app.state.wait_for_ipc(first_run=True)

async def finish_init(app, session_id, workers, dbs):
    """Finish site init"""
    builtins.db = dbs["postgres"]
    builtins.redis_db = dbs["redis"]
    logger.success("Connected to postgres and redis")

    app.state.worker_session = FatesWorkerSession(
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

    # Create the shutdown handler to work around uvicorn faults
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT, signal.SIGQUIT):
        loop.add_signal_handler(sig, shutdown_fates_worker(app))

    # Set the session for use in startup
    session = app.state.worker_session
   
    # Get or create session key
    async def gen_common_secret(key: str):
        dat = await session.redis.get(key)
        if not dat:
            dat = get_token(196)
            await session.redis.set(key, dat, ex=60*60*3*24, nx=True)
            signal.raise_signal(signal.SIGINT)
            os._exit(0)

        dat = dat.decode("utf-8")
        return dat

    session_key = await gen_common_secret("fl:sessionkey")
    app.state.rl_key = await gen_common_secret("fl:rlkey")

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
    builtins.TAGS = tags
    builtins.tags_fixed = calc_tags(tags)

    # Setup sessions (one day expiry)
    app.add_middleware(
        SessionMiddleware, 
        secret_key=session_key, 
        https_only=True,
        max_age=60 * 60 * 12, 
        same_site='strict'
    )  
    
    # Setup sentry
    sentry_sdk.init(sentry_dsn)  # pylint: disable=abstract-class-instantiated
    app.add_middleware(SentryAsgiMiddleware)

    # Setup ratelimiter
    LynxfallLimiter.init(session.redis, identifier=rl_key_func)

    # Setup trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=[site, "127.0.0.1", "0.0.0.0", f"www.{site}"]
    )

    # Add GZip handling
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # Setup exception handling
    codes = (
        403, 
        404, 
        RequestValidationError, 
        ValidationError, 
        500, 
        HTTPException, 
        Exception, 
        StarletteHTTPException
    )

    for code in codes:
        app.add_exception_handler(code, WebError.error_handler)
        
    # Include all routers
    include_routers(app, "Discord", "modules/discord")

    # Fix operation ids
    fix_operation_ids(app)

    # Begin worker sync
    asyncio.create_task(catclient(workers, session))
    logger.debug("Started catclient task")

    # Boast about oht success!
    logger.success(
        f"Fates List worker (pid: {os.getpid()}) bootstrapped successfully!"
    )

        
async def catclient(workers, session):
    """The Fates List Dragon IPC protocol"""
    await session.redis.publish(
        "_worker_fates", 
        f"UP {session.id} {os.getpid()} {workers}"
    )

    pubsub = session.redis.pubsub()
    
    await pubsub.subscribe("_worker_fates")
    async for msg in pubsub.listen():
        if not msg or not isinstance(msg.get("data"), bytes):
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        logger.trace(f"Got {msg}")
        match msg:
            case ("RESTART", tgt):
                if tgt == "*" or (tgt.isdigit() and int(tgt) == os.getpid()):
                    session.up = False
                    logger.info(f"Dying due to sent RESTART call with requestor being {tgt}")

            # IPC going up has no session id yet
            case("REGET", reason):
                # Announce that we are up and sending to repeat a message
                logger.info(f"Sending IPC info due to reget (reason: {reason})")
                await session.redis.publish(
                    "_worker_fates", 
                    f"UP {session.id} {os.getpid()} {workers}"
                )

            # FUP = finally up
            case("FUP", session_id, *worker_lst):
                if session_id != session.id:  # noqa: F821
                    continue
                logger.success("All workers are up!")

                # Finally up!
                try:
                    session.publish_workers(
                        [int(worker) for worker in worker_lst]  # noqa: F821
                    )

                except ValueError:
                    logger.warning(
                        f"Got invalid workers from ipc ({workers})"
                    )
                           
                session.up = True # Site is back up when we FUP
                #asyncio.create_task(vote_reminder(session))

            case _:
                pass  # Ignore the rest for now


async def vote_reminder(session):
    """Vote reminders task"""
    if session.primary_worker():
        events = importlib.import_module("modules.core.events")
        bot_add_event = events.bot_add_event
        reminders = await session.postgres.fetch(
            """SELECT user_id, bot_id FROM user_reminders 
            WHERE remind_time >= NOW() AND resolved = false"""
        )
    
        for reminder in reminders:
            logger.debug(f"Got reminder {reminder}")
            await bot_add_event(
                reminder["bot_id"], 
                enums.APIEvents.vote_reminder, 
                {"user": str(reminder["user_id"])}
            )

            await session.postgres.execute(
                """UPDATE user_reminders SET resolved = true 
                WHERE user_id = $1 AND bot_id = $2""", 
                reminder["user_id"], 
                reminder["bot_id"]
            )
    
        await asyncio.sleep(60 * 15)
        await vote_reminder(session)


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


def shutdown_fates_worker(app):
    """Shutdown the list properly"""
    worker_session = app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis

    async def _close():
        await asyncio.sleep(0)
        await db.close()
        await redis.publish("_worker", f"DOWN WORKER {os.getpid()}")
        await redis.close()
        await asyncio.sleep(0)
        try:
            await app.state.cprof.get_profiler_result()
        except:
            pass
        await asyncio.sleep(0)

    def _signal_handler_entry():
        """Entrypoint for signal handler"""

        # Ensure only one stop task is executed
        if worker_session.dying:
            return

        # We are going to die
        worker_session.dying = True

        # Begin killing fates list
        logger.info("Killing Fates List: ")
        task = asyncio.create_task(_close())
        task.add_done_callback(_gohome)

    def _gohome(_):
        logger.info("Fates List is now down. Going back to the IceWings!")
        os._exit(0)

    return _signal_handler_entry
