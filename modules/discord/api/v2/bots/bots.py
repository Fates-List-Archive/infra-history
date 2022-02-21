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
