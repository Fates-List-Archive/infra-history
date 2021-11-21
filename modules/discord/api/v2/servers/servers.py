from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor

from ..base import API_VERSION
from .models import APIResponse, Guild, GuildRandom, BotStats, BotEvents

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/guilds",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Servers"],
    dependencies=[Depends(id_check("guild"))]
)


from colour import Color

def is_color_like(c):
    try:
        # Converting 'deep sky blue' to 'deepskyblue'
        color = c.replace(" ", "")
        Color(color)
        # if everything goes fine then return True
        return True
    except ValueError: # The color code was not found
        return False


#@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    return await db.fetch("SELECT votes, epoch FROM bot_stats_votes_pm WHERE bot_id = $1", bot_id)

#@router.get("/{bot_id}/tv")
async def get_total_votes(request: Request, bot_id: int):
    return await db.fetchrow("SELECT total_votes AS votes FROM bot_stats_votes WHERE bot_id = $1", bot_id)

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
        res = requests.patch(f"https://fateslist.xyz/api/v2/bots/{guild_id}/token", headers={"Authorization": f"Server {token}"})
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
                global_limit = Limit(times=5, minutes=2),
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
    no_cache: Optional[bool] = False
):
    """
    Fetches server information given a server/guild ID. If not found, 404 will be returned.
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    No cache means cached responses will not be served (may be temp disabled in the case of a DDOS or temp disabled for specific servers as required)
    """
    if len(str(guild_id)) not in [17, 18, 19, 20]:
        return abort(404)

    if not no_cache:
        cache = await redis_db.get(f"guildcache-{guild_id}")
        if cache:
            return orjson.loads(cache)
    

    api_ret = await db.fetchrow(
        "SELECT banner_card, banner_page, guild_count, invite_amount, state, website, votes, invite_channel, nsfw FROM servers WHERE guild_id = $1", 
        guild_id
    )
    if api_ret is None:
        return abort(404)

    api_ret = dict(api_ret)

    api_ret["invite_channel"] = str(api_ret["invite_channel"])

    if not compact:
        extra = await db.fetchrow(
            "SELECT description, long_description_type, long_description, css, keep_banner_decor FROM servers WHERE guild_id = $1",
            guild_id
        )
        api_ret |= dict(extra)

    api_ret["tags"] = [dict(d) for d in (await db.fetch("SELECT tag, emoji FROM server_tags WHERE guild_id = $1", guild_id))]
   
    api_ret["user"] = dict((await db.fetchrow("SELECT guild_id AS id, name_cached AS username, '#0000' AS disc, avatar_cached AS avatar FROM servers WHERE guild_id = $1", guild_id)))
    
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1 AND type = 0", 
        guild_id
    )

    await redis_db.set(f"guildcache-{guild_id}", orjson.dumps(api_ret), ex=60*60*8)

    return api_ret


@router.head("/{guild_id}", operation_id="server_exists")
async def server_exists(request: Request, guild_id: int):
    count = await db.fetchval("SELECT guild_id FROM servers WHERE guild_id = $1", guild_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{guild_id}/widget", operation_id="get_server_widget", deprecated=True)
async def server_widget(request: Request, bt: BackgroundTasks, guild_id: int, format: enums.WidgetFormat, bgcolor: Union[int, str] ='black', textcolor: Union[int, str] ='white'):
    """
    Returns a widget. Superceded by Get Widget API
    """
    return RedirectResponse(f"/api/widgets/{bot_id}?target_type={enums.ReviewType.bot}&format={format.name}&textcolor={textcolor}&bgcolor={bgcolor}")

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
    
