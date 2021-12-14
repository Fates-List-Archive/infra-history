from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, BotEvents

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)

@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    return await db.fetch("SELECT votes, epoch FROM bot_stats_votes_pm WHERE bot_id = $1", bot_id)

@router.patch(
    "/{bot_id}/token", 
    response_model = APIResponse, 
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, minutes=3)
            )
        ), 
        Depends(bot_auth_check)
    ],
    operation_id="regenerate_bot_token"
)
async def regenerate_bot_token(request: Request, bot_id: int):
    """
    Regenerates a bot token. Use this if it is compromised
    

    Example:

    ```py
    import requests

    def regen_token(bot_id, token):
        res = requests.patch(f"https://fateslist.xyz/api/v2/bots/{bot_id}/token", headers={"Authorization": f"Bot {token}"})
        json = res.json()
        if not json["done"]:
            # Handle failures
            ...
        return res, json
    ```
    """
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), bot_id)
    return api_success()

@router.get(
    "/{bot_id}/random", 
    response_model = BotRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=3),
                operation_bucket="random_bot"
            )
        )
    ],
    operation_id="fetch_random_bot"
)
async def fetch_random_bot(request: Request, bot_id: int, lang: str = "default"):
    """
    Fetch a random bot. Bot ID should be the recursive/root bot 0


    Example:
    ```py
    import requests

    def random_bot():
        res = requests.get("https://fateslist.xyz/api/bots/0/random")
        json = res.json()
        if not json.get("done", True):
            # Handle an error in the api
            ...
        return res, json
    ```
    """
    if bot_id != 0:
        return api_error(
            "This bot cannot use the fetch random bot API"
        )

    random_unp = await db.fetchrow(
        "SELECT description, banner_card, state, votes, guild_count, bot_id FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await get_bot(random_unp["bot_id"], worker_session = request.app.state.worker_session)
    if bot_obj is None or bot_obj["disc"] == "0000":
        return await fetch_random_bot(request, lang) # Get a new bot
    bot = bot_obj | dict(random_unp) # Get bot from cache and add that in
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues in javascript
    bot["formatted"] = {
        "votes": human_format(bot["votes"]),
        "guild_count": human_format(bot["guild_count"])
    }
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent XSS attacks in short description
    if not bot["banner_card"]: # Ensure banner is always a string
        bot["banner_card"] = "" 
    return bot

@router.get(
    "/{bot_id}", 
    response_model = Bot, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=2),
                operation_bucket="fetch_bot"
            )
        )
    ],
    operation_id="fetch_bot"
)
async def fetch_bot(
    request: Request, 
    bot_id: int, 
    compact: Optional[bool] = True, 
    offline: Optional[bool] = False,
    no_cache: Optional[bool] = False
):
    """
    Fetches bot information given a bot ID. If not found, 404 will be returned. 

    This endpoint handles both bot IDs and client IDs
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    Setting offline to true -> user will be null and no ownership info will be given. If the bot is no longer on discord, this endpoint will still return if offline is set to true

    No cache means cached responses will not be served (may be temp disabled in the case of a DDOS or temp disabled for specific bots as required)
    """
    if len(str(bot_id)) not in [17, 18, 19, 20]:
        return abort(404)

    if not no_cache:
        cache = await redis_db.get(f"botcache-{bot_id}")
        if cache:
            return orjson.loads(cache)

    api_ret = await db.fetchrow(
        "SELECT bot_id, last_stats_post, banner_card, banner_page, guild_count, shard_count, shards, prefix, invite, invite_amount, features, bot_library AS library, state, website, discord AS support, github, user_count, votes, total_votes, donate, privacy_policy, nsfw, client_id FROM bots WHERE bot_id = $1 OR client_id = $1", 
        bot_id
    )
    if api_ret is None:
        return abort(404)

    bot_id = api_ret["bot_id"]

    api_ret = dict(api_ret)

    if not compact:
        extra = await db.fetchrow(
            "SELECT description, long_description_type, long_description, css, keep_banner_decor FROM bots WHERE bot_id = $1",
            bot_id
        )
        api_ret |= dict(extra)

    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    api_ret["tags"] = [tag["tag"] for tag in tags]
   
    if not offline:
        owners_db = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
        owners = []
        _done = []

        # Preperly sort owners
        for owner in owners_db:
            if owner in _done: continue
        
            _done.append(owner["owner"])
            user = await get_user(owner["owner"])
            main = owner["main"]

            if not user: continue
        
            owner_obj = {
                "user": user,
                "main": main
            }
        
            if main: owners.insert(0, owner_obj)
            else: owners.append(owner_obj)

        api_ret["owners"] = owners
    
    api_ret["features"] = api_ret["features"]
    api_ret["invite_link"] = await invite_bot(bot_id, api = True)
    
    if not offline:
        api_ret["user"] = await get_bot(bot_id)
        if not api_ret["user"]:
            return abort(404)
    
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1", 
        bot_id
    )

    await redis_db.set(f"botcache-{bot_id}", orjson.dumps(api_ret), ex=60*60*8)

    return api_ret


@router.head("/{bot_id}", operation_id="bot_exists")
async def bot_exists(request: Request, bot_id: int):
    count = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{bot_id}/widget", operation_id="get_bot_widget", deprecated=True)
async def bot_widget(request: Request, bt: BackgroundTasks, bot_id: int, format: enums.WidgetFormat, bgcolor: Union[int, str] ='black', textcolor: Union[int, str] ='white'):
    """
    Returns a bots widget. This has been superceded by Get Widget and merely redirects to it now
    """
    return RedirectResponse(f"/api/widgets/{bot_id}?target_type={enums.ReviewType.bot}&format={format.name}&textcolor={textcolor}&bgcolor={bgcolor}")

@router.get(
    "/{bot_id}/ws_events",
    dependencies = [
        Depends(bot_auth_check)
    ],
    operation_id="get_bot_ws_events"
)
async def get_bot_ws_events(request: Request, bot_id: int):
    events = await redis_db.hget(f"bot-{bot_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return orjson.loads(events) 
    

@router.post(
    "/{bot_id}/stats", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1),
                operation_bucket="set_bot_stats"
            ) 
        ),
        Depends(bot_auth_check)
    ],
    operation_id="set_bot_stats"
)
async def set_bot_stats(request: Request, bot_id: int, api: BotStats):
    """
    This endpoint allows you to set the guild + shard counts for your bot


    Example:
    ```py
    # This will use aiohttp and not requests as this is likely to used by discord.py bots
    import aiohttp


    # On dpy, guild_count is usually the below
    guild_count = len(client.guilds)

    # If you are using sharding
    shard_count = len(client.shards)
    shards = client.shards.keys()

    # Optional: User count (this is not accurate for larger bots)
    user_count = len(client.users) 

    async def set_stats(bot_id, token, guild_count, shard_count = None, shards = None, user_count = None):
        json = {"guild_count": guild_count, "shard_count": shard_count, "shards": shards, "user_count": user_count}

        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"https://fateslist.xyz/api/bots/{bot_id}/stats", headers={"Authorization": f"Bot {token}"}, json=json) as res:
                json = await res.json()
                if not json["done"]:
                    # Handle or log this error
                    ...
    ```
    """
    return await _set_bot_stats(request, bot_id, api.dict())

async def _set_bot_stats(request: Request, bot_id: int, api: dict, no_abuse_checks: bool = False):
    lock = await redis_db.get(f"statslock:{bot_id}")
    if lock:
        return api_error("You have been banned from using this API endpoint")

    stats_old = await db.fetchrow(
        "SELECT guild_count, shard_count, shards, user_count FROM bots WHERE bot_id = $1",
        bot_id
    )
    stats_new = api
    stats = {}
    for stat in stats_new.keys():
        if stats_new[stat] is None:
            stats[stat] = stats_old[stat]
        else:
            stats[stat] = stats_new[stat]

    info = await db.fetchrow("SELECT state, client_id FROM bots WHERE bot_id = $1", bot_id)
    state = info["state"]
    app_id = bot_id if (not info["client_id"] or info["client_id"] == bot_id) else info["client_id"]

    async def _flag_bot():
        # Do this later, but return success to evade detection
        key = f"statscheck:{bot_id}"
        redis = request.app.state.worker_session.redis
        check = await redis.incr(key)
        if int(check) <= 5:
            await redis.expire(key, 60*60*8)
            return api_error("You have been caught by our anti-abuse systems. Please try setting your stats using its actual value", ctx="Get your bot certified to avoid anti-abuse. You may only try to post invalid stats 5 times every 8 hours or you will be banned (invalid stats are not set and will only flag you)") 
        await redis.persist(key)
        await redis.set(f"statslock:{bot_id}", 1)
        return api_error("You have been banned from using this API due to triggering our anti-abuse systems in a very short timeframe!")

    if stats["guild_count"] > 300000000000 or stats["shard_count"] > 300000000000 or len(stats["shards"]) > (100 + stats["shard_count"]):
        return await _flag_bot()
    if int(stats["user_count"]) > INT64_MAX:
        return await api_error(f"User count cannot be greater than {INT64_MAX}")

    # Anti abuse checks
    try:
        if state != enums.BotState.certified and not no_abuse_checks:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://japi.rest/discord/v1/application/{app_id}", timeout=15) as resp:
                    if resp.status != 200:
                        return api_error("Our anti-abuse provider is down right now. Please contact Fates List Support if this happens when you try again!")
                    app = await resp.json()
                    try:
                        approx_guild_count = app["data"]["bot"]["approximate_guild_count"]
                    except:
                        return api_error("You need to edit this bot and set a client ID in order to set stats for this bot due to a ID mismatch")
                    if ((stats["guild_count"] - approx_guild_count > 2000 and approx_guild_count > 100000) or 
                    (stats["guild_count"] - approx_guild_count > 20 and approx_guild_count < 1000)):
                        stats["guild_count"] = approx_guild_count
                        await _set_bot_stats(request, bot_id, stats, no_abuse_checks=True)
                        return await _flag_bot()

    except Exception as exc:
        logger.exception("Something happened!")
        return api_error("Our anti-abuse provider is down right now. Please contact Fates List Support if this happens when you try again!")

    await db.execute(
        "UPDATE bots SET last_stats_post = NOW(), guild_count = $1, shard_count = $2, user_count = $3, shards = $4 WHERE bot_id = $5",
        stats["guild_count"],
        stats["shard_count"],
        stats["user_count"],
        stats["shards"],
        bot_id,
    )

    return api_success()
