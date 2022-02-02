"""
Handle API Events, webhooks and websockets
"""

from .imports import *
from .ipc import redis_ipc_new
import aioredis


async def add_ws_event(redis: aioredis.Connection, target: int, ws_event: dict, *, id: Optional[uuid.UUID] = None, type: str = "bot", timeout: int | None = 30) -> None:
    """Create websocket event"""
    if not id:
        id = uuid.uuid4()
    id = str(id)
    if "m" not in ws_event.keys():
        ws_event["m"] = {}
    ws_event["m"]["eid"] = id
    ws_event["m"]["ts"] = time.time()
    await redis_ipc_new(redis, "ADDWSEVENT", msg=ws_event, args=[str(target), str(id), "1" if type == "bot" else "0"], timeout=timeout)

async def bot_get_events(bot_id: int, filter: list = None, exclude: list = None):
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    # Has been replaced by ws events
    return {}

async def bot_add_event(redis: aioredis.Connection, bot_id: int, event: int, context: dict, t: Optional[int] = None, *, send_event: bool = True, guild: bool = False):
    if type(context) is dict:
        pass
    else:
        raise TypeError("Event must be a dict")

    event_time = time.time()
    asyncio.create_task(add_ws_event(redis, bot_id, {"ctx": context, "m": {"t": t if t else -1, "ts": event_time, "e": event}}))
