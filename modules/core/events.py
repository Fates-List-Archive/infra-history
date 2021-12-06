"""
Handle API Events, webhooks and websockets
"""

from .cache import get_bot, get_user
from .imports import *
from .ipc import redis_ipc_new


async def add_ws_event(target: int, ws_event: dict, *, id: Optional[uuid.UUID] = None, type: str = "bot") -> None:
    """Create websocket event"""
    if not id:
        id = uuid.uuid4()
    id = str(id)
    if "m" not in ws_event.keys():
        ws_event["m"] = {}
    ws_event["m"]["eid"] = id
    ws_event["m"]["ts"] = time.time()
    await redis_ipc_new(redis_db, "ADDWSEVENT", msg=ws_event, args=[str(target), str(id), "1" if type == "bot" else "0"])

async def bot_get_events(bot_id: int, filter: list = None, exclude: list = None):
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    # Has been replaced by ws events
    return {}

async def bot_add_event(bot_id: int, event: int, context: dict, t: Optional[int] = None, *, send_event: bool = True, guild: bool = False):
    if type(context) == dict:
        pass
    else:
        raise TypeError("Event must be a dict")

    event_time = time.time()
    asyncio.create_task(add_ws_event(bot_id, {"ctx": context, "m": {"t": t if t else -1, "ts": event_time, "e": event}}))
