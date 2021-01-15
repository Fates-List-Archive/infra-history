from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Bots"]
)

@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")

@router.get("/{bot_id}")
async def bot_index(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, invite, discord, banner, api_token FROM bots WHERE bot_id = $1 ORDER BY votes", bot_id)
    if bot is None:
        return abort(404)
    img_header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
    banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    try:
        res = await requests.get(banner)
        if response.headers['Content-Type'] not in header_list:
            banner = "none"
    except:
        banner = "none"

    bot_info = await get_bot(bot["bot_id"])
    guild = client.get_guild(reviewing_server)
    
    if bot_info:
        bot_obj = {"bot": bot, "bot_id": bot["bot_id"], "avatar": bot_info["avatar"], "website": bot["website"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"], "support": bot['discord'], "invite": bot["invite"], "tags": bot["tags"], "library": bot['library'], "banner": banner, "token": bot["api_token"]}
    else:
        return abort(404)
    # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    form = await Form.from_formdata(request)
    return templates.TemplateResponse("bot.html", {"request": request, "username": request.session.get("username", False), "bot": bot_obj, "tags_fixed": tags_fixed, "form": form, "avatar": request.session.get("avatar")})


@router.get("/description/{bot_id}")
async def bot_desc(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"bot":bot})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"
