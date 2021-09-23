from typing import Optional

from modules.core import *

from ..base import API_VERSION
from .models import BotListStats, BotQueueGet

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - System"]
)

@router.get(
    "/blstats", 
    response_model = BotListStats,
    operation_id="blstats"
)
async def get_botlist_stats(
    request: Request,
    worker_session = Depends(worker_session)
):
    """
        Returns uptime and stats about the list.
        uptime - The current uptime for the given worker
        pid - The pid of the worker you are connected to
        up - Whether the databases are up on this worker
        dup - Always true now, but used to be: Whether we have connected to discord on this worker
        bot_count_total - The bot count of the list
        bot_count - The approved and certified bots on the list
        workers - The worker pids
    """
    up = worker_session.up
    db = worker_session.postgres
    if up:
        bot_count_total = await db.fetchval("SELECT COUNT(1) FROM bots")
        bot_count = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    else:
        bot_count = 0
        bot_count_total = 0
    return {
        "uptime": time.time() - worker_session.start_time, 
        "pid": os.getpid(), 
        "up": up, 
        "dup": True,
        "bot_count": bot_count, 
        "bot_count_total": bot_count_total,
        "workers": worker_session.workers
    }

@router.get("/features")
def get_features(request: Request):
    """Returns all of the features the list supports and information about them. Keys indicate the feature id and value is feature information. The value should but may not always have a name, type and a description keys in the json"""
    return features

@router.get("/tags")
def get_tags(request: Request):
    """These are the tags the list supports. The key is the tag name and the value is the iconify class we use"""
    return TAGS

@router.get(
    "/is_staff",
    operation_id="check_staff_member"
)
async def check_staff_member(request: Request, user_id: int, min_perm: int):
    """Admin route to check if a user is staff or not"""
    staff = await is_staff(staff_roles, user_id, min_perm, json = True)
    return {"staff": staff[0], "perm": staff[1], "sm": staff[2]}

@router.get(
    "/queue/bots", 
    response_model=BotQueueGet,
    operation_id="get_bot_queue"
)
async def get_bot_queue(
    request: Request, 
    state: enums.BotState = enums.BotState.pending, 
    verifier: int = None, 
    worker_session = Depends(worker_session)
):
    """Admin API to get the bot queue"""
    db = worker_session.postgres
    if verifier:
        bots = await db.fetch("SELECT bot_id, prefix, description FROM bots WHERE state = $1 AND verifier = $2 ORDER BY created_at ASC", state, verifier)
    bots = await db.fetch("SELECT bot_id, prefix, description FROM bots WHERE state = $1 ORDER BY created_at ASC", state)
    return {"bots": [{"user": await get_bot(bot["bot_id"]), "prefix": bot["prefix"], "invite": await invite_bot(bot["bot_id"], api = True), "description": bot["description"]} for bot in bots]}

@router.get(
    "/staff_roles",
    operation_id="get_staff_roles"
)
def get_staff_roles(request: Request):
    """Return all the staff roles so they can be used by our manager bot"""
    return staff_roles
