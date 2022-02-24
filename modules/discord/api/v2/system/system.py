import hmac
from http.client import responses
from typing import Optional

from modules.core import *
from hashlib import sha512
import hmac

from ..base import API_VERSION, responses
from ..base_models import APIResponse, HTMLAPIResponse
from .models import AddBotInfo, BotFeatures, BotIndex, BotQueueGet, BotStatsFull, Search, TagSearch, BotVanity, Partners, StaffRoles, IsStaff, Troubleshoot

router = APIRouter(
    prefix=f"/api/v{API_VERSION}",
    include_in_schema=True,
    tags=[f"API v{API_VERSION} - System"],
)

def get_uptime():
    with open("/proc/uptime") as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds

@router.get(
    "/blstats-full",
    response_model=BotStatsFull
)
async def stats_page(request: Request, full: bool = False):
    """
    Returns the full set of botlist stats

    This includes blstats data as well now which is:

    **uptime** - The current uptime for the given worker. All workers reboot periodically to avoid memory leaks
    so this will mostly be low

    **pid** - The pid of the worker you are connected to

    **up** - Whether the databases are up on this worker

    **server_uptime** - How long the Fates List Server has been up for totally

    **bot_amount_total** - The bot count of the list

    **bot_amount** - Renamed to bot_amount. The number of approved and certified bots on the list

    **workers** - The worker pids. This is sorted and retrived from dragon IPC if not directly available on the worker
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres

    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    if full:
        return abort(400) # We cannot handle full as of now
        denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
        banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    return {
        "bot_amount_total": await db.fetchval("SELECT COUNT(1) FROM bots"),
        "certified": certified,
        "bot_amount": bot_amount,
        "queue": queue,
        "denied": denied if full else [],
        "denied_amount": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.denied),
        "banned": banned if full else [],
        "banned_amount": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.banned),
        "under_review": under_review,
        "uptime": time.time() - worker_session.start_time,
        "server_uptime": get_uptime(),
        "pid": os.getpid(),
        "up": True,
        "workers": [],
    }


@router.get("/is_staff", response_model=IsStaff)
async def check_staff_member(request: Request,
                             user_id: int,
                             min_perm: int = 2):
    """Admin route to check if a user is staff or not"""
    redis = request.app.state.worker_session.redis
    staff = await is_staff(staff_roles, user_id, min_perm, redis=redis, json=True)
    return {"staff": staff[0], "perm": staff[1], "sm": staff[2]}


@router.get("/bots/filter",
            response_model=BotQueueGet,
            operation_id="get_bots_filtered")
async def get_bots_filtered(
        request: Request,
        state: List[enums.BotState] = Query(
            ..., description="Bot states like ?state=0&state=6"),
        verifier: int = None,
        limit: int = 100,
        offset: int = 0,
        worker_session=Depends(worker_session),
):
    """
    API to get all bots filtered by its state

    Limit must be less than or equal to 100

    **This API now guarantees that the bot list is only what you
    request**
    """
    if limit > 100:
        return api_error("Limit must be less than or equal to 100")

    db = worker_session.postgres
    redis = worker_session.redis

    bots = []

    paginator = f"LIMIT {limit} OFFSET {offset}"

    if verifier:
        for s in state:
            _bots = await db.fetch(
                f"SELECT bot_id, guild_count, website, discord AS support, votes, long_description, prefix, description, state FROM bots WHERE state = $1 AND verifier = $2 ORDER BY created_at ASC {paginator}",
                s,
                verifier,
            )
            bots += _bots

    state_str = f"WHERE state = {state[0]}"
    for s in state[1:]:
        state_str += f" OR state = {s}"
    _bots = await db.fetch(
        f"SELECT bot_id, guild_count, website, discord AS support, votes, long_description, prefix, description, state FROM bots {state_str} ORDER BY created_at ASC {paginator}",
    )
    bots += _bots

    return {
        "bots": [{
            "user":
            await get_bot(bot["bot_id"], worker_session=worker_session),
            "prefix":
            bot["prefix"],
            "invite":
            await invite_bot(db, redis, bot["bot_id"], api=False),
            "description": bot["description"],
            "state": bot["state"],
            "guild_count": bot["guild_count"],
            "votes": bot["votes"],
            "long_description": bot["long_description"],
            "website": bot["website"],
            "support": bot["support"],
            "owners":
            await db.fetch(
                "SELECT owner AS user_id, main FROM bot_owner WHERE bot_id = $1",
                bot["bot_id"],
            ),
            "tags":
            await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1",
                           bot["bot_id"]),
        } for bot in bots]
    }


@router.get("/staff_roles", response_model=StaffRoles, operation_id="get_staff_roles")
def get_staff_roles(request: Request):
    """Return all staff roles and their role ids if you ever wanted them..."""
    return staff_roles

@router.get("/staff-apps/qibli/{id}")
async def short_url(request: Request, id: uuid.UUID):
    """
    Gets the qibli data for a id
    """
    redis = request.app.state.worker_session.redis
    data = await redis.get(f"sapp:{id}")
    if not data:
        return abort(404)
    return orjson.loads(data)