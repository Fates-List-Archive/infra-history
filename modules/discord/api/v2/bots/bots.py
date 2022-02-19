import urllib.parse

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, SettingsPage

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)

@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    db = request.app.state.worker_session.postgres
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
    db = request.app.state.worker_session.postgres
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), bot_id)
    return api_success()

@router.head("/{bot_id}")
async def bot_exists(request: Request, bot_id: int):
    db = request.app.state.worker_session.postgres
    
    check = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    if not check:
        return PlainTextResponse("", status_code=404)
    return PlainTextResponse("", status_code=200)

@router.get("/{bot_id}/_sunbeam/invite")
async def get_bot_invite(request: Request, bot_id: int, user_id: int = 0):
    """
    Internally used by sunbeam for inviting users.

    While the data you get from this API is sanitized because
    it is actually rendered for users, it is *not* recommended
    to rely or use this API outside of internal use cases. Data
    is unstructured and will constantly change. **This API is not
    backwards compatible whatsoever**

    Additionally, this API *will* trigger a WS Invite Event.

    To protect against scraping, this endpoint requires a proper
    Frostpaw header to be set.

    This API will also be heavily monitored. If we find you attempting
    to abuse this API endpoint or doing anything out of the ordinary with
    it, you may be IP or user banned. Calling it once or twice is OK but
    automating it is not. Use the Get Bot API instead for automation.

    **This API is only documented because it's in our FastAPI backend and
    to be complete**
    """
    if not request.headers.get("Frostpaw"):
        return abort(404)
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    invite = await invite_bot(db, redis, bot_id, user_id = user_id)
    if invite is None:
        return abort(404)
    
    # Uncomment if sunbeam fails
    # JS sucks so much, its redirects don't work
    # id = uuid.uuid4()
    #await redis.set(f"sunbeam-redirect-{id}", invite, ex=60*30)
    #return {"fallback": str(id), "invite": invite}
    return {"invite": invite}

@router.get(
    "/{bot_id}/_sunbeam/settings",
    dependencies=[
        Depends(user_auth_check)
    ],
)
async def get_bot_settings(request: Request, bot_id: int, user_id: int):
    """
    Internally used by sunbeam for bot settings.

    While the data you get from this API is sanitized because
    it is actually rendered for users, it is *not* recommended
    to rely or use this API outside of internal use cases. Data
    is unstructured and will constantly change. **This API is not
    backwards compatible whatsoever**

    To protect against scraping, this endpoint requires a proper
    Frostpaw header to be set.

    This API will also be heavily monitored. If we find you attempting
    to abuse this API endpoint or doing anything out of the ordinary with
    it, you may be IP or user banned. Calling it once or twice is OK but
    automating it is not. Use the Get Bot API instead for automation.

    **This API is only documented because it's in our FastAPI backend and
    to be complete**
    """
    if not request.headers.get("Frostpaw"):
        return abort(404)
    # TODO: make this just use vanilla owners_html
    def sunbeam_get(owners_lst: tuple):
        owners_html = "<br/>".join([f"<a class='long-desc-link' href='/profile/{owner[0]}'>{owner[1]}</a>" for owner in owners_lst if owner])
        return owners_html

    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis

    check = await is_bot_admin(bot_id, user_id, worker_session=worker_session)
    if (not check and bot_id !=
            798951566634778641):  # Fates list main bot is staff viewable
        return api_error("You are not allowed to edit this bot!", status_code=403)

    bot = await db.fetchrow(
        "SELECT bot_id, client_id, api_token, state, prefix, bot_library AS library, invite, website, banner_card, banner_page, long_description, description, webhook, webhook_secret, webhook_type, discord AS support, flags, github, features, long_description_type, css, donate, privacy_policy, nsfw, keep_banner_decor, page_style FROM bots WHERE bot_id = $1",
        bot_id,
    )

    if not bot:
        return abort(404)

    bot = dict(bot)

    if bot["css"]:
        bot["css"] = bot["css"].replace("\\n", "\n").replace("\\t", "\t")

    # Will be removed once discord is no longer de-facto platform
    bot["platform"] = "discord"

    if flags_check(bot["flags"], enums.BotFlag.system):
        bot["system_bot"] = True
    else:
        bot["system_bot"] = False

    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    bot["tags"] = [tag["tag"] for tag in tags]
    owners = await db.fetch(
        "SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
    if not owners:
        return api_error("Invalid owners set. Contact Fates List Support")
        
    owners_lst = [(await get_user(obj["owner"],
                                  user_only=True,
                                  worker_session=worker_session))
                  for obj in owners
                  if obj["owner"] is not None and obj["main"]]

    owners_lst_extra = [(await get_user(obj["owner"],
                                        user_only=True,
                                        worker_session=worker_session))
                        for obj in owners
                        if obj["owner"] is not None and not obj["main"]]

    bot["owners_html"] = sunbeam_get(owners_lst + owners_lst_extra)

    bot["client_id"] = str(bot["client_id"])

    bot["extra_owners"] = ",".join(
        [str(o["owner"]) for o in owners if not o["main"]])
    bot["user"] = await get_bot(bot_id, worker_session=worker_session)
    if not bot["user"]:
        return abort(404)

    vanity = await db.fetchval(
        "SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bot_id)
    bot["vanity"] = vanity

    bot["bot_id"] = str(bot_id)

    context = {
        "perm": (await is_staff(None, user_id, 4, redis=redis))[1],
        "tags": [tag["id"] for tag in request.app.state.worker_session.tags_fixed],
        "features": list(features.keys()),
    }

    return {
        "data": bot,
        "context": context
    }

@router.head("/{bot_id}", operation_id="bot_exists")
async def bot_exists(request: Request, bot_id: int):
    db = request.app.state.worker_session.postgres
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
    redis = request.app.state.worker_session.redis
    events = await redis.hget(f"bot-{bot_id}", key = "ws")
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
    db = request.app.state.worker_session.postgres

    stats_old = await db.fetchrow(
        "SELECT guild_count, shard_count, shards, user_count FROM bots WHERE bot_id = $1",
        bot_id
    )
    stats = {}
    for stat, value in api.items():
        if value is None:
            stats[stat] = stats_old[stat]
        else:
            stats[stat] = value

    info = await db.fetchrow("SELECT state, flags, client_id FROM bots WHERE bot_id = $1", bot_id)
    state = info["state"]
    if state not in (enums.BotState.approved, enums.BotState.certified):
        return api_error("This endpoint can only be used by approved and certified bots!")
    if flags_check(info["flags"], enums.BotFlag.stats_locked):
        logger.warning("This bot has been banned from this API endpoint")
        return api_error("You have been banned from using this API endpoint")
    app_id = bot_id if (not info["client_id"] or info["client_id"] == bot_id) else info["client_id"]

    async def _flag_bot():
        # Do this later, but return success to evade detection
        key = f"statscheck:{bot_id}"
        redis = request.app.state.worker_session.redis
        check = await redis.incr(key)
        logger.warning(f"Bot flagged {stats}")
        if int(check) <= 5:
            await redis.expire(key, 60*60*8)
            return api_error("You have been caught by our anti-abuse systems. Please try setting your stats using its actual value", ctx="Get your bot certified to avoid anti-abuse. You may only try to post invalid stats 5 times every 8 hours or you will be banned (invalid stats are not set and will only flag you)") 
        await redis.persist(key)
        await db.execute("UPDATE bots SET flags = flags || $1 WHERE bot_id = $2", [enums.BotFlag.stats_locked], bot_id) 
        logger.warning("Bot has been banned")
        return api_error("You have been banned from using this API due to triggering our anti-abuse systems in a very short timeframe!")

    if stats["guild_count"] > 300000000000 or stats["shard_count"] > 300000000000 or len(stats["shards"]) > (100 + stats["shard_count"]):
        return await _flag_bot()
    if int(stats["user_count"]) > INT64_MAX:
        return await api_error(f"User count cannot be greater than {INT64_MAX}")

    # Anti abuse checks
    headers = {"Authorization": japi_key} # Lets hope this doesnt break shit
    try:
        if state != enums.BotState.certified and not no_abuse_checks:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://japi.rest/discord/v1/application/{app_id}", headers=headers) as resp:
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
