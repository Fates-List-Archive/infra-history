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

import aioredis
import asyncpg
import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.routing import APIRoute
from lynxfall.core.classes import Singleton
from starlette.middleware.base import BaseHTTPMiddleware

from loguru import logger
from modules.core.ipc import redis_ipc_new
from modules.models import enums

sys.pycache_prefix = "data/pycache"

class FatesListRequestHandler(BaseHTTPMiddleware):
    """Request Handler for Fates List"""
    def __init__(self, app):
        super().__init__(app)
                        
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        if request.headers.get("method"):
            request.scope["method"] = request.headers.get("method", "GET")
                               
        start_time = time.time()
        
        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-PID"] = str(os.getpid())
           
        return response if response else PlainTextResponse("Something went wrong!")
        
class FatesWorkerSession(Singleton):  # pylint: disable=too-many-instance-attributes
    """Stores a worker session"""

    def __init__(
        self,
        *, 
        app: FastAPI,
        session_id: str,
        postgres: asyncpg.Pool,
        redis: aioredis.Connection,
        worker_count: int
    ):
        self.id = session_id
        self.postgres = postgres
        self.redis = redis
        self.worker_count = worker_count
        self.app = app

        # Record basic stats and initially set workers to None
        self.start_time = time.time()

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

    dbs = await setup_db()

    app.state.worker_session = FatesWorkerSession(
        app=app,
        session_id=session_id,
        postgres=dbs["postgres"],
        redis=dbs["redis"],
        worker_count=workers
    )
               
    # Include all routers
    from modules.infra.widgets.widgets import router
    app.include_router(router)

    # Fix operation ids
    fix_operation_ids(app)

    logger.success(
        f"Fates List worker (pid: {os.getpid()}) bootstrapped successfully!"
    )


async def rl_key_func(request: Request) -> str:
    return None

async def setup_db():
    """Function to setup the asyncpg connection pool"""
    postgres = await asyncpg.create_pool()
    redis = await aioredis.from_url('redis://localhost:1001', db=1)
    return {"postgres": postgres, "redis": redis}
