from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor

from ..base import API_VERSION
from .models import APIResponse, Guild, GuildRandom

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/guilds",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Servers"],
    dependencies=[Depends(id_check("guild"))]
)

@router.patch(
    "/{guild_id}/token", 
    response_model = APIResponse, 
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, minutes=3)
            )
        ), 
        Depends(server_auth_check)
    ],
    operation_id="regenerate_server_token"
)
async def regenerate_server_token(request: Request, guild_id: int):
    """
    Regenerates a server token. Use this if it is compromised and you don't have time to use slash commands
    

    Example:

    ```py
    import requests

    def regen_token(guild_id, token):
        res = requests.patch(f"https://fateslist.xyz/api/v2/guilds/{guild_id}/token", headers={"Authorization": f"Server {token}"})
        json = res.json()
        if not json["done"]:
            # Handle failures
            ...
        return res, json
    ```
    """
    await db.execute("UPDATE servers SET api_token = $1 WHERE guild_id = $2", get_token(256), guild_id)
    return api_success()

@router.get(
    "/{guild_id}/random", 
    response_model = GuildRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=5),
                operation_bucket="random_guild"
            )
        )
    ],
    operation_id="fetch_random_server"
)
async def fetch_random_server(request: Request, guild_id: int, lang: str = "default"):
    """
    Fetch a random server. Server ID should be the recursive/root server 0.


    Example:
    ```py
    import requests

    def random_server():
        res = requests.get("https://fateslist.xyz/api/guilds/0/random")
        json = res.json()
        if not json.get("done", True):
            # Handle an error in the api
            ...
        return res, json
    ```
    """
    if guild_id != 0:
        return api_error(
            "This guild cannot use the fetch random guild API"
        )

    random_unp = await db.fetchrow(
        "SELECT description, banner_card, state, votes, guild_count, guild_id FROM servers WHERE (state = 0 OR state = 6) AND description IS NOT NULL ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await db.fetchrow("SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1", random_unp["guild_id"])
    bot_obj = dict(bot_obj) | {"disc": "0000", "status": 1, "bot": True}
    bot = bot_obj | dict(random_unp) # Get bot from cache and add that in
    bot["guild_id"] = str(bot["guild_id"]) # Make sure bot id is a string to prevent corruption issues in javascript
    bot["formatted"] = {
        "votes": human_format(bot["votes"]),
        "guild_count": human_format(bot["guild_count"])
    }
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent XSS attacks in short description
    if not bot["banner_card"]: # Ensure banner is always a string
        bot["banner_card"] = "" 
    return bot

@router.get(
    "/{guild_id}", 
    response_model = Guild, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1),
                operation_bucket="fetch_guild"
            )
        )
    ],
    operation_id="fetch_server"
)
async def fetch_server(
    request: Request, 
    guild_id: int, 
    compact: Optional[bool] = True, 
    no_cache: Optional[bool] = False,
    sensitive: bool = True
):
    """
    Fetches server information given a server/guild ID. If not found, 404 will be returned.
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    No cache means cached responses will not be served (may be temp disabled in the case of a DDOS or temp disabled for specific servers as required)

    Setting sensitive to true will expose sensitive info like invite channel, user whitelist/blacklist etc
    """
    if len(str(guild_id)) not in [17, 18, 19, 20]:
        return abort(404)

    if not no_cache:
        cache = await redis_db.get(f"guildcache-{guild_id}")
        if cache:
            return orjson.loads(cache)
    

    api_ret = await db.fetchrow(
        "SELECT banner_card, banner_page, guild_count, invite_amount, state, website, total_votes, login_required, votes, nsfw, tags AS _tags FROM servers WHERE guild_id = $1", 
        guild_id
    )
    if api_ret is None:
        return abort(404)

    api_ret = dict(api_ret)

    if sensitive:
        await server_auth_check(guild_id, request.headers.get("Authorization", ""))
        sensitive_dat = await db.fetchrow("SELECT invite_channel, user_whitelist, user_blacklist FROM servers WHERE guild_id = $1", guild_id)
        api_ret |= dict(sensitive_dat)
        api_ret["invite_channel"] = str(api_ret["invite_channel"]) if api_ret["invite_channel"] else None

    if not compact:
        extra = await db.fetchrow(
            "SELECT description, long_description_type, long_description, css, keep_banner_decor FROM servers WHERE guild_id = $1",
            guild_id
        )
        api_ret |= dict(extra)

    api_ret["tags"] = [dict(await db.fetchrow("SELECT name, id, iconify_data FROM server_tags WHERE id = $1", id)) for id in api_ret["_tags"]]
   
    api_ret["user"] = dict(await db.fetchrow("SELECT guild_id AS id, name_cached AS username, '0000' AS disc, avatar_cached AS avatar FROM servers WHERE guild_id = $1", guild_id))
    
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1 AND type = 0", 
        guild_id
    )
    
    if not sensitive:
        await redis_db.set(f"guildcache-{guild_id}", orjson.dumps(api_ret), ex=60*60*8)

    return api_ret

@router.get("/{guild_id}/_sunbeam")
async def get_server_page(request: Request, guild_id: int, bt: BackgroundTasks, lang: str = "en"):
    """
    Internally used by sunbeam for server page getting.
    """
    if not request.headers.get("Frostpaw"):
        return abort(404)
    data = await db.fetchrow(
        """SELECT banner_page AS banner, keep_banner_decor, guild_count, nsfw, state, invite_amount, avatar_cached, name_cached, votes, css, description, 
        long_description, long_description_type, website, tags AS _tags, js_allowed, flags FROM servers WHERE guild_id = $1""",
        guild_id
    )
    if not data:
        logger.info("Something happened!")
        return abort(404)
    data = dict(data)
    data["resources"] = await db.fetch("SELECT id, resource_title, resource_link, resource_description FROM resources WHERE target_id = $1 AND target_type = $2", guild_id, enums.ReviewType.server.value)
    if not data["description"]:
        data["description"] = await default_server_desc(data["name_cached"], guild_id)
    data["user"] = {
        "username": data["name_cached"],
        "avatar": data["avatar_cached"]
    }
    data["tags_fixed"] = [(await db.fetchrow("SELECT id, name, iconify_data FROM server_tags WHERE id = $1", id)) for id in data["_tags"]]
    context = {"type": "server", "replace_list": constants.long_desc_replace_tuple, "id": str(guild_id), "index": "/servers"}
    data["type"] = "server"
    data["id"] = str(guild_id)
    bt.add_task(add_ws_event, guild_id, {"m": {"e": enums.APIEvents.server_view}, "ctx": {"user": request.session.get('user_id'), "widget": False}}, type = "server")
    # Ensure server banner_page is disabled if not approved or certified
    if data["state"] not in (enums.BotState.approved, enums.BotState.certified, enums.BotState.private_viewable):
        data["banner"] = None
        data["js_allowed"] = False

    data = sanitize_bot(data, lang)

    base = {
        "type": "server", 
        "promos": [],
        "replace_list": constants.long_desc_replace_tuple_sunbeam,
        "fl_cache_ver": -1,
    }
    return {"data": data} | base


@router.get(
    "/{guild_id}/_sunbeam/invite"
)
async def get_server_invite(request: Request, guild_id: int):
    """
    Internally used by sunbeam for inviting users.

    **Usage of this API without explicit permission from said servers
    is not allowed**

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
    auth = request.headers.get("Frostpaw-Auth", "")
    if auth and "|" in auth:
        user_id, token = auth.split("|")
        try:
            user_id = int(user_id)
        except Exception:
            return api_error("Invalid User ID specified, are you logged in?")
        auth = await user_auth_check(user_id, token)
    else:
        user_id = 0
    invite = await redis_ipc_new(redis_db, "GUILDINVITE", args=[str(guild_id), str(user_id)])
    if invite is None:
        return await get_server_invite(request, guild_id)
    invite = invite.decode("utf-8")
    if invite.startswith("https://"):
        return {"invite": invite}
    return api_error(invite)



@router.head("/{guild_id}", operation_id="server_exists")
async def server_exists(request: Request, guild_id: int):
    count = await db.fetchval("SELECT guild_id FROM servers WHERE guild_id = $1", guild_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{guild_id}/widget", operation_id="get_server_widget", deprecated=True)
async def server_widget(request: Request, bt: BackgroundTasks, guild_id: int, format: enums.WidgetFormat, bgcolor: Union[int, str] ='black', textcolor: Union[int, str] ='white'):
    """
    Returns a widget. Superceded by Get Widget API
    """
    return RedirectResponse(f"/api/widgets/{guild_id}?target_type={enums.ReviewType.server}&format={format.name}&textcolor={textcolor}&bgcolor={bgcolor}")

@router.get(
    "/{guild_id}/ws_events",
    dependencies = [
        Depends(server_auth_check)
    ],
    operation_id="get_server_ws_events"
)
async def get_server_ws_events(request: Request, guild_id: int):
    events = await redis_db.hget(f"server-{guild_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return orjson.loads(events) 
    
