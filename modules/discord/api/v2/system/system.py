from typing import Optional

from modules.core import *

from ..base import API_VERSION
from .models import BotListStats, BotQueueGet, BotVanity, BotIndex, BotSearch

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - System"]
)

def get_uptime():
    with open('/proc/uptime') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


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
        
        server_uptime - How long the Fates List Server has been up for totally

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
    if not worker_session.workers:
        os._exit(0) # Force die
    return {
        "uptime": time.time() - worker_session.start_time,
        "server_uptime": get_uptime(),
        "pid": os.getpid(), 
        "up": up, 
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
async def check_staff_member(request: Request, user_id: int, min_perm: int = 2):
    """Admin route to check if a user is staff or not"""
    staff = await is_staff(staff_roles, user_id, min_perm, json = True)
    return {"staff": staff[0], "perm": staff[1], "sm": staff[2]}

@router.get(
    "/bots/filter", 
    response_model=BotQueueGet,
    operation_id="get_bots_filtered"
)
async def get_bots_filtered(
    request: Request, 
    state: enums.BotState = enums.BotState.pending, 
    verifier: int = None, 
    worker_session = Depends(worker_session)
):
    """API to get all bots filtered by its state"""
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
    """Return all staff roles and their role ids if you ever wanted them..."""
    return staff_roles

@router.get(
    "/code/{vanity}",
    response_model = BotVanity
)
async def get_vanity(request: Request, vanity: str):
    """Gets information about a vanity given a vanity code"""
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get(
    "/index",
    response_model=BotIndex
)
async def get_index(request: Request, type: enums.ReviewType = enums.ReviewType.bot):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True, type=type)

@router.get(
    "/search", 
    response_model = BotSearch,
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def search_list(request: Request, q: str, target_type: enums.SearchType):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for. Target type is the type to search for"""
    return await render_search(request = request, q = q, api = True, target_type=target_type)
