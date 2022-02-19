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
    "/_sunbeam/add-bot",
    response_model=AddBotInfo,
)
async def add_bot_info(request: Request, user_id: int):
    redis = request.app.state.worker_session.redis
    context = {
        "perm": (await is_staff(None, user_id, 4, redis=redis))[1],
        "tags": [tag["id"] for tag in request.app.state.worker_session.tags_fixed],
        "features": list(features.keys()),
    }
    return context

@router.get(
    "/_sunbeam/troubleshoot",
    response_model=Troubleshoot
)
async def troubleshoot_api(request: Request, user_id: int | None = None):
    """
    Internal API used by sunbeam for troubleshooting issues

    Used in https://fateslist.xyz/frostpaw/troubleshoot

    This requires a Frostpaw header to be properly set
    """
    if not request.headers.get("Frostpaw"):
        return abort(404)
    data = {
        "req_user_agent": request.headers.get("User-Agent"),
        "pid": os.getpid(),
        "cf_ip": request.headers.get("X-Forwarded-For"),
        "user": None
    }

    if user_id:
        data["user"] = await get_user(user_id, worker_session=request.app.state.worker_session)

    return data

@router.post(
    "/_csp",
    response_model=APIResponse
)
async def csp_report(request: Request):
    """
    This is where CSP reports should be sent to.

    CSP reports should not happen in practice.

    **These requests are logged to loguru**
    """
    try:
        logger.warning("CSP Report: ", (await request.json()))
    except:
        pass
    return api_success()


@router.post("/sellix-webhook")
async def sellix_webhook(request: Request):
    """
    **Warning**: Only documented for internal use

    Can be used by staff in case you didn't get the actual order
    """
    body: bytes = await request.body()
    hash = hmac.new(
        sellix_secret.encode(),
        body,
        sha512
    )

    try:
        data = orjson.loads(body)
    except:
        return abort(400)

    valid_webhook = True
    if hash.hexdigest() != request.headers.get("X-Sellix-Signature"):
        print(hash.hexdigest(), request.headers.get("X-Sellix-Signature"), "Sig Mismatch")
        valid_webhook = False
        # Check if the order is valid first before returning a 401
        try:
            id = data["uniqid"]
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    f"https://dev.sellix.io/v1/orders/{id}", 
                    headers={
                        "Authorization": f"Bearer {sellix_api_key}"
                    }
                ) as res:
                    if res.status > 400:
                        return api_error(f"Got status code {res.status} for this order")
                    else:
                        data = await res.json()
        except:
            return api_error("Not a valid webhook", status_code=401)

    event = request.headers.get("X-Sellix-Event", "")

    if event == "order:created":
        user_id = data["custom_fields"]["Discord ID"]
        
    return api_success("WIP", valid_webhook=valid_webhook)


@router.get("/top-spots")
def get_top_spots(request: Request):
    bots_top = []
    servers_top = []

    return {"bots": bots_top, "servers": servers_top}


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

    if not worker_session.workers or worker_session.worker_count != len(
            worker_session.workers):
        workers = await redis_ipc_new(worker_session.redis, "WORKERS", worker_session=worker_session)
        if not workers:
            return abort(503)
        worker_session.workers = orjson.loads(workers)
        worker_session.workers.sort()
        worker_session.up = True  # If workers is actually existant, then it's up

    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    if full:
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
        "up": worker_session.up,
        "workers": worker_session.workers,
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

@router.get("/search/tags", response_model=TagSearch, dependencies=[])
async def search_by_tag(request: Request, 
                        tag: str,
                        target_type: enums.SearchType):

    db = request.app.state.worker_session.postgres

    if target_type == enums.SearchType.bot:
        fetch = await db.fetch(
            "SELECT DISTINCT bots.bot_id, bots.description, bots.state, bots.banner_card AS banner, bots.votes, bots.guild_count FROM bots INNER JOIN bot_tags ON bot_tags.bot_id = bots.bot_id WHERE bot_tags.tag = $1 AND (bots.state = 0 OR bots.state = 6) ORDER BY bots.votes DESC LIMIT 15",
            tag,
        )
        tags = request.app.state.worker_session.tags_fixed  # Gotta love python
    else:
        fetch = await db.fetch(
            "SELECT DISTINCT guild_id, description, state, banner_card AS banner, votes, guild_count FROM servers WHERE state = 0 AND tags && $1",
            [tag],
        )
        tags = await db.fetch(
            "SELECT DISTINCT id, name, iconify_data FROM server_tags")
    search_bots = await parse_index_query(
        request.app.state.worker_session,
        fetch,
        type=enums.ReviewType.bot
        if target_type == enums.SearchType.bot else enums.ReviewType.server,
    )
    return {
        "search_res": search_bots,
        "tags_fixed": tags,
        "query": tag,
    }


@router.get("/partners", response_model=Partners)
async def get_partners(request: Request):
    """
    Gets the partner list.
    """
    return partners


@router.get(
    "/vote-reminders", 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, seconds=30)
            )
        ),
    ]
)
async def get_all_vote_reminders(request: Request):
    """Get vote reminders"""
    worker_session: FatesWorkerSession = request.app.state.worker_session
    reminders = await worker_session.postgres.fetch("SELECT user_id::text, vote_reminders::text[], vote_reminder_channel::text FROM users WHERE vote_reminders != '{}'")
    reminders_lst = []
    for reminder in reminders:
        can_vote = []
        for bot in reminder["vote_reminders"]:
            vote_epoch = await worker_session.redis.ttl(f"vote_lock:{reminder['user_id']}")
            if vote_epoch < 0:
                can_vote.append(bot)
        _reminder = dict(reminder)
        _reminder["can_vote"] = can_vote
        reminders_lst.append(_reminder)
    return {"reminders": reminders_lst}

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