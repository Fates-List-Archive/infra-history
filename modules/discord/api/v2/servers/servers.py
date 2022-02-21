from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder

from ..base import API_VERSION
from .models import APIResponse, Guild, GuildRandom
import bleach

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
    db = request.app.state.worker_session.postgres
    await db.execute("UPDATE servers SET api_token = $1 WHERE guild_id = $2", get_token(256), guild_id)
    return api_success()

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
    worker_session = request.app.state.worker_session
    redis = worker_session.redis
    if not request.headers.get("Frostpaw"):
        return abort(404)
    auth = request.headers.get("Frostpaw-Auth", "")
    if auth and "|" in auth:
        user_id, token = auth.split("|")
        try:
            user_id = int(user_id)
        except Exception:
            return api_error("Invalid User ID specified, are you logged in?")
        auth = await user_auth_check(request, user_id, token)
    else:
        user_id = 0
    invite = await redis_ipc_new(redis, "GUILDINVITE", args=[str(guild_id), str(user_id)], worker_session=worker_session)
    if invite is None:
        return await get_server_invite(request, guild_id)
    invite = invite.decode("utf-8")
    if invite.startswith("https://"):
        return {"invite": invite}
    return api_error(invite)

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
    redis = request.app.state.worker_session.redis
    events = await redis.hget(f"server-{guild_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return orjson.loads(events) 
    
