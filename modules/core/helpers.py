"""
Helper functions for mundane tasks like getting maint, promotion or bot commands
and/or setting bot stats and voting for a bot. Also has replace tuples to be handled
"""

import asyncpg
import aioredis

from .auth import *
from .cache import *
from .imports import *

def worker_session(request: Request):
    return request.app.state.worker_session

async def add_ws_event(redis: aioredis.Connection, target: int, ws_event: dict, *, id: Optional[uuid.UUID] = None, type: str = "bot", timeout: int | None = 30) -> None:
    """Create websocket event"""
    return # Being remade in baypaw

async def bot_get_events(*_, **__):
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    # Has been replaced by ws events
    return {}

async def bot_add_event(redis: aioredis.Connection, bot_id: int, event: int, context: dict, t: Optional[int] = None, *, send_event: bool = True, guild: bool = False):
    return # No point in using a broken API
