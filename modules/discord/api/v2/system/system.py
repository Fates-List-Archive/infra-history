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
    return abort(408)

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
    return abort(408)
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