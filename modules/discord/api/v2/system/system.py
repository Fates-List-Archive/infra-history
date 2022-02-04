import hmac
from http.client import responses
from typing import Optional

from modules.core import *
from hashlib import sha512
import hmac

from ..base import API_VERSION, responses
from ..base_models import APIResponse, HTMLAPIResponse
from .models import AddBotInfo, BotFeatures, BotIndex, BotListStats, BotQueueGet, BotStatsFull, Search, TagSearch, BotVanity, Partners, StaffRoles, IsStaff, Troubleshoot

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
    "/_sunbeam/reviews/{target_id}",
    response_model=HTMLAPIResponse,
)
async def review_page(
    request: Request, 
    target_id: int, 
    target_type: enums.ReviewType,
    page: int = 1, 
    user_id: int | None = 0,
):
    """
    Returns:

    **html** - The html to render in iframe
    """
    if target_id > INT64_MAX:
        return api_error("id out of int64 range")
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session, target_id, page=page, target_type=target_type)
    context = {
        "id": str(target_type),
        "user_id": str(user_id),
        "type": "bot" if target_type == enums.ReviewType.bot else "server",
        "reviews": {
            "average_rating": float(reviews[1])
        },
    }
    data = {
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4],
    }

    template = await templates.TemplateResponse(
        "reviews.html", 
        {
            "request": request, 
            "data": {
                "user": {}
            }
        } | data, 
        context = context)
    return {"html": template.body}

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
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    if full:
        denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
        banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    data = {
        "certified": certified,
        "bot_amount": bot_amount,
        "queue": queue,
        "denied": denied if full else [],
        "denied_amount": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.denied),
        "banned": banned if full else [],
        "banned_amount": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.banned),
        "under_review": under_review,
    }
    return data

@router.get("/blstats", response_model=BotListStats)
async def get_botlist_stats(request: Request,
                            worker_session=Depends(worker_session)):
    """
    Returns uptime and stats about the list.

    **uptime** - The current uptime for the given worker. All workers reboot periodically to avoid memory leaks
    so this will mostly be low

    **pid** - The pid of the worker you are connected to

    **up** - Whether the databases are up on this worker

    **server_uptime** - How long the Fates List Server has been up for totally

    **bot_count_total** - The bot count of the list

    **bot_count** - The approved and certified bots on the list

    **workers** - The worker pids. This is sorted and retrived from dragon IPC if not directly available on the worker
    """
    db = worker_session.postgres
    bot_count_total = await db.fetchval("SELECT COUNT(1) FROM bots")
    bot_count = await db.fetchval(
        "SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    if not worker_session.workers or worker_session.worker_count != len(
            worker_session.workers):
        workers = await redis_ipc_new(worker_session.redis, "WORKERS", worker_session=worker_session)
        if not workers:
            return abort(503)
        worker_session.workers = orjson.loads(workers)
        worker_session.workers.sort()
        worker_session.up = True  # If workers is actually existant
    return {
        "uptime": time.time() - worker_session.start_time,
        "server_uptime": get_uptime(),
        "pid": os.getpid(),
        "up": worker_session.up,
        "bot_count": bot_count,
        "bot_count_total": bot_count_total,
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


@router.get("/code/{vanity}", response_model=BotVanity)
async def get_vanity(request: Request, vanity: str):
    """
    Gets information about a vanity given a vanity code
    
    This is used by sunbeam in handling vanities
    """
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    vb = await vanity_bot(db, redis, vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get("/index", response_model=BotIndex)
async def get_index(request: Request,
                    type: enums.ReviewType = enums.ReviewType.bot):
    """
    Returns the bot/server index JSON

    This is internally used by sunbeam to render the index page
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    top_voted = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [0], type=type)
    new_bots = await do_index_query(worker_session, add_query = "ORDER BY created_at DESC", state = [0], type=type)
    certified_bots = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [6], type=type)

    if type == enums.ReviewType.bot:
        tags = request.app.state.worker_session.tags_fixed
    else:
        tags = await db.fetch("SELECT id, name, iconify_data, owner_guild FROM server_tags")

    base_json = {
        "tags_fixed": tags, 
        "top_voted": top_voted, 
        "new_bots": new_bots, 
        "certified_bots": certified_bots, 
        "features": features if type == enums.ReviewType.bot else None,
    }

    return base_json

async def pack_search(worker_session, q: str):
    db = worker_session.postgres
    packs_db = await db.fetch(
        """
        SELECT DISTINCT bot_packs.id, bot_packs.icon, bot_packs.banner, 
        bot_packs.created_at, bot_packs.owner, bot_packs.bots, 
        bot_packs.description, bot_packs.name FROM (
            SELECT id, icon, banner, 
            created_at, owner, bots, 
            description, name, unnest(bots) AS bot_id FROM bot_packs
        ) bot_packs
        INNER JOIN bots ON bots.bot_id = bot_packs.bot_id 
        INNER JOIN users ON users.user_id = bot_packs.owner
        WHERE bot_packs.name ilike $1 OR bot_packs.owner::text 
        ilike $1 OR users.username ilike $1 OR bots.bot_id::text ilike $1 
        OR bots.username_cached ilike $1
        """,
        f'%{q}%',
    )
    packs = []
    for pack in packs_db:
        resolved_bots = []
        ids = []
        for id in pack["bots"]:
            bot = await get_bot(id, worker_session=worker_session)
            bot["description"] = await db.fetchval("SELECT description FROM bots WHERE bot_id = $1", id)
            resolved_bots.append(bot)
            ids.append(str(id))

        packs.append({
            "id": str(pack["id"]),
            "name": pack["name"],
            "description": pack["description"],
            "bots": ids,
            "resolved_bots": resolved_bots,
            "owner": await get_user(pack["owner"], worker_session=worker_session),
            "icon": pack["icon"],
            "banner": pack["banner"],
            "created_at": pack["created_at"]
        })
    return packs


@router.get(
    "/search",
    response_model=Search,
    dependencies=[],
)
async def search_list(request: Request, q: str):
    """
    Searches the list for any bot/server/profile available
    Q is the query to search for. 
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis
    
    if q == "":
        return abort(404)
    
    cache = await redis.get(f"search:{q}")
    if cache:
        return orjson.loads(cache)

    data = {}
    data["tags"] = {}

    data["bots"] = await db.fetch(
        """SELECT DISTINCT bots.bot_id,
        bots.description, bots.banner_card AS banner, bots.state, 
        bots.votes, bots.guild_count, bots.nsfw FROM bots 
        INNER JOIN bot_owner ON bots.bot_id = bot_owner.bot_id 
        WHERE (bots.description ilike $1 
        OR bots.long_description ilike $1 
        OR bots.username_cached ilike $1 
        OR bot_owner.owner::text ilike $1) 
        AND (bots.state = $2 OR bots.state = $3) 
        ORDER BY bots.votes DESC, bots.guild_count DESC LIMIT 6
        """, 
        f'%{q}%',
        enums.BotState.approved,
        enums.BotState.certified
    )

    data["tags"]["bots"] = request.app.state.worker_session.tags_fixed
    
    data["servers"] = await db.fetch(
        """SELECT DISTINCT servers.guild_id,
        servers.description, servers.banner_card AS banner, servers.state,
        servers.votes, servers.guild_count, servers.nsfw FROM servers
        WHERE (servers.description ilike $1
        OR servers.long_description ilike $1
        OR servers.name_cached ilike $1) AND servers.state = $2
        ORDER BY servers.votes DESC, servers.guild_count DESC LIMIT 6
        """,
        f'%{q}%',
        enums.BotState.approved
    )

    data["tags"]["servers"] = await db.fetch("SELECT id, name, iconify_data, owner_guild FROM server_tags")
    
    data["packs"] = await pack_search(worker_session, q)

    profiles = await db.fetch(
        """SELECT DISTINCT users.user_id, users.description FROM users 
        INNER JOIN bot_owner ON users.user_id = bot_owner.owner 
        INNER JOIN bots ON bot_owner.bot_id = bots.bot_id 
        WHERE ((bots.state = 0 OR bots.state = 6) 
        AND (bots.username_cached ilike $1 OR bots.description ilike $1 OR bots.bot_id::text ilike $1)) 
        OR (users.username ilike $1) LIMIT 12""", 
        f'%{q}%'
    )
    profile_obj = []
    for profile in profiles:
        profile_info = await get_user(profile["user_id"], worker_session = worker_session)
        if profile_info:
            profile_obj.append({"banner": None, "description": profile["description"], "user": profile_info})
    data["profiles"] = profile_obj

    data["bots"] = await parse_index_query(
        worker_session,
        data["bots"],
        type=enums.ReviewType.bot
    )
    
    data["servers"] = await parse_index_query(
        worker_session,
        data["servers"],
        type=enums.ReviewType.server
    )

    data["bots"] = [dict(obj) for obj in data["bots"]]
    data["servers"] = [dict(obj) for obj in data["servers"]]
    data["packs"] = [dict(obj) for obj in data["packs"]]
    data["tags"]["servers"] = [dict(obj) for obj in data["tags"]["servers"]]
    data["features"] = features

    await redis.set(f"search:{q}", orjson.dumps(data), ex=60*5)

    return data

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