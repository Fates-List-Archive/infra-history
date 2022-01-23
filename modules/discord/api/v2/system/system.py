import hmac
from hashlib import md5
from typing import Optional

from modules.core import *
from hashlib import sha512
import hmac

from ..base import API_VERSION
from .models import BotIndex, BotListStats, BotQueueGet, BotSearch, BotVanity, Partners, StaffRoles, IsStaff

router = APIRouter(
    prefix=f"/api/v{API_VERSION}",
    include_in_schema=True,
    tags=[f"API v{API_VERSION} - System"],
)

def get_uptime():
    with open("/proc/uptime") as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds

@router.get("/_sunbeam/troubleshoot")
async def troubleshoot_api(request: Request):
    """
    Internal API used by sunbeam for troubleshooting issues

    Used in https://fateslist.xyz/frostpaw/troubleshoot

    This requires a Frostpaw header to be properly set
    """
    if not request.headers.get("Frostpaw"):
        return abort(404)
    data = {
        "user_id": request.session.get("user_id"), 
        "logged_in": "user_id" in request.session.keys(),
        "user_agent": request.headers.get("User-Agent"),
        "pid": os.getpid(),
        "cf_ip": request.headers.get("X-Forwarded-For")
    }

    if data["logged_in"]:
        data["user"] = await get_user(data["user_id"], worker_session=request.app.state.worker_session)

    return {"message": "Please send a screenshot of this page and send it to staff (or our support server)", "data": data}

@router.post("/_csp")
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


@router.get("/blstats-full")
async def stats_page(request: Request, full: bool = False):
    """
    Returns the full set of botlist stats
    """
    worker_session = request.app.state.worker_session
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
        "full": full
    }
    return data

@router.get("/blstats", response_model=BotListStats, operation_id="blstats")
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
        workers = await redis_ipc_new(worker_session.redis, "WORKERS")
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

@router.get("/features")
def get_features(request: Request):
    """Returns all of the features the list supports and information about them. Keys indicate the feature id and value is feature information. The value should but may not always have a name, type and a description keys in the json"""
    return features

@router.get("/tags")
def get_tags(request: Request):
    """
    These are the *bot* tags the list has. The key is the tag name and the value is the iconify class we use
    
    **To get server tags, call the server index endpoint**
    """
    return TAGS


@router.get("/is_staff", operation_id="check_staff_member", response_model=IsStaff)
async def check_staff_member(request: Request,
                             user_id: int,
                             min_perm: int = 2):
    """Admin route to check if a user is staff or not"""
    staff = await is_staff(staff_roles, user_id, min_perm, json=True)
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

    **Warning: This api does not guarantee you will get the same 
    number of bots as what you put in limit and may add more 
    but not less. If you don't want this, specify only one state
    to ensure you are not requesting bots paginated commonly
    across multiple set states**
    """
    db = worker_session.postgres

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

    for s in state:
        _bots = await db.fetch(
            f"SELECT bot_id, guild_count, website, discord AS support, votes, long_description, prefix, description, state FROM bots WHERE state = $1 ORDER BY created_at ASC {paginator}",
            s,
        )
        bots += _bots

    return {
        "bots": [{
            "user":
            await get_bot(bot["bot_id"]),
            "prefix":
            bot["prefix"],
            "invite":
            await invite_bot(bot["bot_id"], api=True),
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
    """Gets information about a vanity given a vanity code"""
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get("/index", response_model=BotIndex)
async def get_index(request: Request,
                    type: enums.ReviewType = enums.ReviewType.bot):
    """For any potential Android/iOS app, crawlers etc."""
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    top_voted = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [0], type=type)
    new_bots = await do_index_query(worker_session, add_query = "ORDER BY created_at DESC", state = [0], type=type)
    certified_bots = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [6], type=type)

    if type == enums.ReviewType.bot:
        tags = tags_fixed
    else:
        tags = await db.fetch("SELECT id, name, iconify_data, owner_guild FROM server_tags")

    base_json = {
        "tags_fixed": tags, 
        "top_voted": top_voted, 
        "new_bots": new_bots, 
        "certified_bots": certified_bots, 
    }

    if type == enums.ReviewType.server:
        context = {"type": "server", "index": "/servers"}
    else:
        context = {"type": "bot"}

    return base_json


@router.get(
    "/search",
    response_model=BotSearch,
    dependencies=[],
)
async def search_list(request: Request, q: str, target_type: enums.SearchType):
    """For any potential Android/iOS app, crawlers etc. 
    Q is the query to search for. 
    Target type is the type to search for
    
    **Profile search auto-redirects**
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    
    if q == "":
        return abort(404)

    if target_type == enums.SearchType.bot:
        data = await db.fetch(
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
        tags = tags_fixed
    elif target_type == enums.SearchType.server:
        data = await db.fetch(
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
        tags = await db.fetch("SELECT id, name, iconify_data, owner_guild FROM server_tags")
    else:
        return RedirectResponse(f"/api/v2/search/profiles?q={q}", status_code=301)
    search_bots = await parse_index_query(
        worker_session,
        data,
        type=enums.ReviewType.bot if target_type == enums.SearchType.bot else enums.ReviewType.server
    )
    return {"search_res": search_bots, "tags_fixed": tags, "query": q}

@router.get("/search/profiles", response_model=BotSearch)
async def search_by_profile(request: Request, q: str):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    if not q.replace(" ", ""):
        profiles = []
    else:
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
    return {"search_res": profile_obj, "tags_fixed": [], "query": q}



@router.get("/search/tags", response_model=BotSearch, dependencies=[])
async def search_by_tag(request: Request, tag: str,
                        target_type: enums.SearchType):
    if target_type == enums.SearchType.bot:
        fetch = await db.fetch(
            "SELECT DISTINCT bots.bot_id, bots.description, bots.state, bots.banner_card AS banner, bots.votes, bots.guild_count FROM bots INNER JOIN bot_tags ON bot_tags.bot_id = bots.bot_id WHERE bot_tags.tag = $1 AND (bots.state = 0 OR bots.state = 6) ORDER BY bots.votes DESC LIMIT 15",
            tag,
        )
        tags = tags_fixed  # Gotta love python
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
        "profile_search": False,
        "type": target_type.name,
        "query": tag,
    }


@router.get("/partners", response_model=Partners)
async def get_partners(request: Request):
    """
    Gets the partner list.
    """
    return partners


@router.get("/_sunbeam/redirect")
async def sunbeam_redirect(request: Request, id: uuid.UUID):
    """
    Internally used by sunbeam for redirects as a fallback.

    While the data you get from this API is sanitized because
    it is actually rendered for users, it is *not* recommended
    to rely or use this API outside of internal use cases. Data
    is unstructured and will constantly change. **This API is not
    backwards compatible whatsoever**

    Additionally, this API *will* trigger a WS Invite Event.

    This API will also be heavily monitored. If we find you attempting
    to abuse this API endpoint or doing anything out of the ordinary with
    it, you may be IP or user banned. Calling it once or twice is OK but
    automating it is not. Use the Get Bot API instead for automation.

    **This API is only documented because it's in our FastAPI backend and
    to be complete**
    """
    url = await redis_db.get(f"sunbeam-redirect-{id}")
    if id:
        return RedirectResponse(url.decode())
    return abort(404)
