import io

from starlette.responses import StreamingResponse
from fastapi import Response
from modules.core import constants
import bleach
import markdown
from lxml.html.clean import Cleaner
from modules.models import constants

from ..core import *

cleaner = Cleaner()

router = APIRouter(
    prefix = "/server",
    tags = ["Servers"],
    include_in_schema = False
)

@router.get("/{guild_id}")
async def guild_page(request: Request, guild_id: int, bt: BackgroundTasks, rev_page: int = 1, api: bool = False):
    data = await db.fetchrow("SELECT banner_page AS banner, keep_banner_decor, guild_count, nsfw, state, invite_amount, avatar_cached, name_cached, votes, css, description, long_description, long_description_type, website, tags AS _tags, js_allowed FROM servers WHERE guild_id = $1", guild_id)
    if not data:
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
    # Ensure server banner_page is disable if not approved or certified
    if data["state"] not in (enums.BotState.approved, enums.BotState.certified, enums.BotState.private_viewable):
        data["banner"] = None
        data["js_allowed"] = False

    data["description"] = intl_text(data['description'], request.session.get("site_lang", "default"))
    data['long_description'] = intl_text(data['long_description'], request.session.get("site_lang", "default"))

    if data["long_description_type"] == enums.LongDescType.markdown_pymarkdown: # If we are using markdown
        data["long_description"] = emd(markdown.markdown(data['long_description'], extensions = md_extensions))

    data["long_description"] = ireplacem(constants.long_desc_replace_tuple, data["long_description"])

    user_js_allowed = request.session.get("js_allowed", True)
    if not user_js_allowed or not data["js_allowed"]:
        try:
            data["long_description"] = cleaner.clean_html(data["long_description"]) 
        except:
            data["long_description"] = bleach.clean(data["long_description"])

    return await templates.TemplateResponse("bot_server.html", {"request": request, "replace_last": replace_last, "data": data} | data, context = context)

@router.get("/{guild_id}/reviews_html")
async def guild_review_page(request: Request, guild_id: int, page: int = 1):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session, guild_id, page=page, target_type=enums.ReviewType.server)
    context = {
        "id": str(guild_id),
        "type": "server",
        "reviews": {
            "average_rating": float(reviews[1])
        },
        "index": "/servers"
    }
    data = {
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4],
    }

    user = {}
    
    return await templates.TemplateResponse("ext/reviews.html", {"request": request, "data": {"user": user}} | data, context = context)


@router.get("/{guild_id}/invite")
async def guild_invite(request: Request, guild_id: int):
    if "user_id" not in request.session.keys():
        user_id = 0
    else:
        user_id = int(request.session.get("user_id"))
    invite = await redis_ipc_new(redis_db, "GUILDINVITE", args=[str(guild_id), str(user_id)])
    if invite is None:
        return abort(404)
    invite = invite.decode("utf-8")
    if invite.startswith("https://"):
        return RedirectResponse(invite)
    return await templates.e(request, invite)

@router.get("/{guild_id}/vote")
async def vote_bot_get(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT bot_id, votes, state FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return abort(404)
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    bot = dict(bot) | bot_obj
    return await templates.TemplateResponse("vote.html", {"request": request, "bot": bot})
