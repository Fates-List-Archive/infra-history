from ..deps import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List

discord_o = Oauth()

router = APIRouter(
    prefix = "/api",
    include_in_schema = True
)

class PromoDelete(BaseModel):
    promo_id: Optional[uuid.UUID] = None

class Promo(BaseModel):
    title: str
    info: str
    css: Optional[str] = None
    type: int

class PromoObj(BaseModel):
    promotions: list

class PromoPatch(Promo):
    promo_id: uuid.UUID

class APIResponse(BaseModel):
    done: bool
    reason: Optional[str] = None

@router.get("/bots/{bot_id}/promotions", tags = ["API"], response_model = PromoObj)
async def get_promotion(request:  Request, bot_id: int):
    return {"promotions": (await get_promotions(bot_id))}

@router.delete("/bots/{bot_id}/promotions", tags = ["API"], response_model = APIResponse)
async def delete_promotion(request: Request, bot_id: int, promo: PromoDelete, Authorization: str = Header("INVALID_API_TOKEN")):
    """Deletes a promotion for a bot or deletes all promotions from a bot (WARNING: DO NOT DO THIS UNLESS YOU KNOW WHAT YOU ARE DOING).

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    if promo.promo_id is not None:
        eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", promo.promo_id)
        if eid is None:
            return {"done":  False, "reason": "NO_PROMOTION_FOUND"}
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", id, promo.promo_id)
    else:
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1", id)
    return {"done":  True, "reason": None}

@router.put("/bots/{bot_id}/promotions", tags = ["API"], response_model = APIResponse)
async def create_promotion(request: Request, bot_id: int, promo: Promo, Authorization: str = Header("INVALID_API_TOKEN")):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic

    """
    if len(promo.title) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    if promo.type not in [1, 2, 3]:
        return {"done":  False, "reason": "INVALID_PROMO_TYPE"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    await add_promotion(id, promo.title, promo.info, promo.css, promo.type)
    return {"done":  True, "reason": None}

@router.patch("/bots/{bot_id}/promotions", tags = ["API"], response_model = APIResponse)
async def edit_promotion(request: Request, bot_id: int, promo: PromoPatch, Authorization: str = Header("INVALID_API_TOKEN")):
    """Edits an promotion for a bot given its promotion ID.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Promotion ID**: This is the ID of the promotion you wish to edit 

    """
    if len(promo.title) < 3:
        return ORJSONResponse({"done":  False, "reason": "TEXT_TOO_SMALL"}, status_code = 400)
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", promo.promo_id, bot_id)
    if pid is None:
        return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND"}, status_code = 400)
    await db.execute("UPDATE bot_promotions SET title = $1, info = $2 WHERE bot_id = $3 AND id = $4", promo.title, promo.info, bot_id, promo.promo_id)
    return {"done": True, "reason": None}

@router.patch("/bots/{bot_id}/token", tags = ["API"], response_model = APIResponse)
async def regenerate_token(request: Request, bot_id: int, Authorization: str = Header("INVALID_API_TOKEN")):
    """Regenerate the API token

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), id["bot_id"])
    return {"done": True, "reason": None}

class RandomBotsAPI(BaseModel):
    bot_id: str
    description: str
    banner: str
    certified: bool
    username: str
    avatar: str
    servers: str
    invite: str
    votes: int

@router.get("/bots/random", tags = ["API"], response_model = RandomBotsAPI)
async def random_bots_api(request: Request):
    random_unp = await db.fetchrow("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false ORDER BY RANDOM() LIMIT 1") # Unprocessed
    bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp)
    bot["bot_id"] = str(bot["bot_id"])
    bot["servers"] = human_format(bot["servers"])
    bot["description"] = bot["description"].replace("<", "").replace(">", "")
    return bot

class Bot(BaseModel):
    id: str
    description: str
    tags: list
    html_long_description: bool
    long_description: Optional[str] = None
    server_count: int
    shard_count: Optional[int] = 0
    user_count: int
    shards: Optional[list] = []
    prefix: str
    library: str
    invite: str
    invite_amount: int
    main_owner: str
    extra_owners: list
    owners: list
    features: list
    queue: bool
    banned: bool
    certified: bool
    website: Optional[str] = None
    support: Optional[str] = None
    github: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: Optional[str] = None
    reviews: Optional[list] = None # Compact
    sensitive: dict
    promotions: Optional[List[Promo]] = {}
    maint: dict
    average_stars: Optional[float] = None # Conpact
    username: str
    avatar: str
    disc: str
    status: int
    donate: Optional[str] = None

@router.get("/bots/{bot_id}", tags = ["API"], response_model = Bot, dependencies=[Depends(RateLimiter(times=5, minutes=3))])
async def get_bots_api(request: Request, bot_id: int, compact: Optional[bool] = False, Authorization: str = Header("INVALID_API_TOKEN")):
    """Gets bot information given a bot ID. If not found, 404 will be returned. If a proper API Token is provided, sensitive information (System API Events will also be provided)"""
    api_ret = await db.fetchrow("SELECT bot_id AS id, description, tags, html_long_description, long_description, servers AS server_count, shard_count, shards, prefix, invite, invite_amount, owner AS main_owner, extra_owners, features, bot_library AS library, queue, banned, certified, website, discord AS support, github, user_count, votes, css, donate FROM bots WHERE bot_id = $1", bot_id)
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    if compact:
        del api_ret["css"]
        del api_ret["long_description"]
    if api_ret["features"] is None:
        api_ret["features"] = []
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    api_ret = api_ret | bot_obj
    api_ret["main_owner"] = str(api_ret["main_owner"])
    if api_ret["extra_owners"] is None:
        api_ret["extra_owners"] = []
    api_ret["extra_owners"] = [str(eo) for eo in api_ret["extra_owners"]]
    api_ret["owners"] = [api_ret["main_owner"]] + api_ret["extra_owners"]
    api_ret["id"] = str(api_ret["id"])
    if Authorization is not None:
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(Authorization))
        if check is None or check["bot_id"] != bot_id:
            sensitive = False
        else:
            sensitive = True
    else:
        sensitive = False
    if sensitive:
        api_ret["sensitive"] = await get_events(bot_id = bot_id)
    else:
        api_ret["sensitive"] = {}
    api_ret["promotions"] = await get_promotions(bot_id = bot_id)
    maint = await in_maint(bot_id = bot_id)
    api_ret["maint"] = {"status": maint[0], "reason": maint[1]}
    vanity = await db.fetchrow("SELECT vanity_url FROM vanity WHERE redirect = $1", bot_id)
    if vanity is None:
        api_ret["vanity"] = None
    else:
        api_ret["vanity"] = vanity["vanity_url"]
    if not compact:
        reviews = await parse_reviews(bot_id)
        api_ret["reviews"] = reviews[0]
        api_ret["average_stars"] = float(reviews[1])
    return api_ret

class BotCommandAdd(BaseModel):
    slash: int # 0 = no, 1 = guild, 2 = global
    name: str
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: str

class APIResponseCommandAdd(APIResponse):
    id: uuid.UUID

class CommandObj(BaseModel):
    commands: list

@router.get("/bots/{bot_id}/commands", tags = ["API"], response_model = CommandObj)
async def get_bot_commands_api(request:  Request, bot_id: int):
    return {"commands": (await db.fetch("SELECT id, slash, name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE bot_id = $1", bot_id))}


@router.put("/bots/{bot_id}/commands", tags = ["API"], response_model = APIResponseCommandAdd, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def add_bot_command_api(request: Request, bot_id: int, command: BotCommandAdd, Authorization: str = Header("INVALID_API_TOKEN"), force_add: Optional[bool] = False):
    """
        Self explaining command. Note that if force_add is set, the API will not check if your command already exists and will forcefully add it, this may lead to duplicate commands on your bot. If ret_id is not set, you will not get the command id back in the api response
    """
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)

    if force_add is False:
        check = await db.fetchrow("SELECT name FROM bot_commands WHERE name = $1 AND bot_id = $2", command.name, bot_id)
        if check is not None:
            return ORJSONResponse({"done":  False, "reason": "COMMAND_ALREADY_EXISTS"}, status_code = 400)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, slash, name, description, args, examples, premium_only, notes, doc_link) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)", id, bot_id, command.slash, command.name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link)
    return {"done": True, "reason": None, "id": id}

class BotCommandEdit(BaseModel):
    id: uuid.UUID
    slash: Optional[int] = None # 0 = no, 1 = guild, 2 = global
    name: Optional[str] = None
    description: Optional[str] = None
    args: Optional[list] = None
    examples: Optional[list] = None
    premium_only: Optional[bool] = None
    notes: Optional[list] = None
    doc_link: Optional[str] = None

@router.patch("/bots/{bot_id}/commands", tags = ["API"], response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def edit_bot_command_api(request: Request, bot_id: int, command: BotCommandEdit, Authorization: str = Header("INVALID_API_TOKEN")):
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    data = await db.fetchrow(f"SELECT id, slash, name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    if data is None:
        return abort(404)

    # Check values to be editted
    command_dict = command.dict()
    for key in command_dict.keys():
        if command_dict[key] is None: 
            command_dict[key] = data[key]
    await db.execute("UPDATE bot_commands SET slash = $2, name = $3, description = $4, args = $5, examples = $6, premium_only = $7, notes = $8, doc_link = $9 WHERE id = $1", command_dict["id"], command_dict["slash"], command_dict["name"], command_dict["description"], command_dict["args"], command_dict["examples"], command_dict["premium_only"], command_dict["notes"], command_dict["doc_link"])
    return {"done": True, "reason": None}

class BotCommandDelete(BaseModel):
    id: uuid.UUID

@router.delete("/bots/{bot_id}/commands", tags = ["API"], response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def delete_bot_command_api(request: Request, bot_id: int, command: BotCommandDelete, Authorization: str = Header("INVALID_API_TOKEN")):
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    return {"done": True, "reason": None}

class BotVoteCheck(BaseModel):
    votes: int
    voted: bool
    vote_right_now: bool
    vote_epoch: int
    time_to_vote: int

@router.get("/bots/{bot_id}/votes", tags = ["API"], response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("INVALID_API_TOKEN")):
    """Endpoint to check amount of votes a user has."""
    if user_id is None:
        return dict((await db.fetchrow("SELECT votes FROM bots WHERE bot_id = $1", bot_id))) | {"vote_epoch": 0, "voted": False, "time_to_vote": 1, "vote_right_now": False}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    voters = await db.fetchrow("SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    if voters is None:
        return {"votes": 0, "voted": False, "vote_epoch": 0, "time_to_vote": 0, "vote_right_now": True}
    voter_count = len(voters["timestamps"])
    vote_epoch = await db.fetchrow("SELECT vote_epoch FROM users WHERE user_id = $1", user_id)
    if vote_epoch is None:
        vote_epoch = 0
    else:
        vote_epoch = vote_epoch["vote_epoch"]
    WT = 60*60*8 # Wait Time
    time_to_vote = WT - (time.time() - vote_epoch)
    if time_to_vote < 0:
        time_to_vote = 0
    return {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": vote_epoch, "time_to_vote": time_to_vote, "vote_right_now": time_to_vote == 0}

@router.get("/bots/{bot_id}/votes/timestamped", tags = ["API"])
async def timestamped_get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("INVALID_API_TOKEN")):
    """Endpoint to check amount of votes a user has with timestamps. This does not return whether a user can vote"""
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    elif user_id is not None:
        ldata = await db.fetch("SELECT userid, timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    else:
        ldata = await db.fetch("SELECT userid, timestamps FROM bot_voters WHERE bot_id = $1", int(bot_id))
    ret = {}
    for data in ldata:
        ret[str(data["userid"])] = data["timestamps"]
    return {"user": "timestamp"} | ret

# TODO
#@router.get("/templates/{code}", tags = ["Core API"])
#async def get_template_api(request: Request, code: str):
#    guild =  await client.fetch_template(code).source_guild
#    return template

class BotStats(BaseModel):
    guild_count: int
    shard_count: Optional[int] = None
    shards: Optional[list] = None
    user_count: Optional[int] = None

@router.post("/bots/{bot_id}/stats", tags = ["API"], response_model = APIResponse)
async def set_bot_stats_api(request: Request, bt: BackgroundTasks, bot_id: int, api: BotStats, Authorization: str = Header("INVALID_API_TOKEN")):
    """
    This endpoint allows you to set the guild + shard counts for your bot
    """
    id = await db.fetchrow("SELECT bot_id, shard_count, shards, user_count FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    if api.shard_count is None:
        shard_count = id["shard_count"]
    else:
        shard_count = api.shard_count
    if api.shards is None:
        shards = id["shards"]
    else:
        shards = api.shards
    if api.user_count is None:
        user_count = id["user_count"]
    else:
        user_count = api.user_count
    bt.add_task(set_stats, bot_id = id["bot_id"], guild_count = api.guild_count, shard_count = shard_count, shards = shards, user_count = user_count)
    return {"done": True, "reason": None}

# set_stats(*, bot_id: int, guild_count: int, shard_count: int, user_count: Optiona;int] = None):

class APISMaint(BaseModel):
    mode: int = 1
    reason: str

@router.post("/bots/{bot_id}/maintenances", tags = ["API"], response_model = APIResponse)
async def set_maintenance_mode(request: Request, bot_id: int, api: APISMaint, Authorization: str = Header("INVALID_API_TOKEN")):
    """This is just an endpoing for enabling or disabling maintenance mode. As of the new API Revamp, this isi the only way to add a maint

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token

    **Mode**: Whether you want to enter or exit maintenance mode. Setting this to 1 will enable maintenance and setting this to 0 will disable maintenance mode. Different maintenance modes are planned
    """
    
    if api.mode not in [0, 1]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await add_maint(id["bot_id"], api.mode, api.reason)
    return {"done": True, "reason": None}

@router.get("/features/{name}", tags = ["API"])
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]

@router.get("/tags/{name}", tags = ["API"])
async def get_tags_api(request: Request, name: str):
    """Gets a tag given its internal name (custom_prefix, open_source etc)"""
    if name not in TAGS.keys():
        return abort(404)
    return {"name": name.replace("_", " ").title(), "iconify_data": TAGS[name], "id": name}


class VanityAPI(BaseModel):
    type: str
    redirect: str

@router.get("/vanity/{vanity}", tags = ["API"], response_model = VanityAPI)
async def get_vanity(request: Request, vanity: str):
    vb = await vanity_bot(vanity, compact = True)
    if vb is None:
        return abort(404)
    return {"type": vb[0], "redirect": vb[1]}

@router.get("/bots/ext/index", tags = ["API (Extras)"])
async def bots_index_page_api_do(request: Request):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True)

@router.get("/bots/ext/search", tags = ["API (Extras)"])
async def bots_search_page(request: Request, query: str):
    """For any potential Android/iOS app, crawlers etc. Query is the query to search for"""
    return await render_search(request = request, q = query, api = True)

async def ws_send_events():
    manager.fl_loaded = True
    while True:
        sent_id = []
        for ws in manager.active_connections:
            for bid in ws.bot_id:
                ws_events = {str(bid): (await redis_db.hget(str(bid), key = "ws"))}
                if ws_events[str(bid)] is not None:
                    # Make sure payload is made a dict
                    ws_events[str(bid)] = orjson.loads(ws_events[str(bid)])
                    for key in ws_events[str(bid)].copy().keys():
                        sent_id.append(sent_id)
                        if key == "status" or key in sent_id:
                            continue
                        try:
                            ws_events[str(bid)][key] = orjson.loads(ws_events[str(bid)][key])
                            try:
                                del ws_events[str(bid)]["status"]
                                del ws_events[str(bid)][key]["status"]
                            except:
                                pass
                            del ws_events[str(bid)][key]['id']
                        except:
                            pass
                    rc = await manager.send_personal_message({"payload": "EVENTS", "type": "EVENTS_V1", "data": ws_events}, ws)
                    await redis_db.hdel(str(bid), "ws")
        sent_id = [] # Empty the list

class MDRequest(BaseModel):
    markdown: str

class MDResponse(BaseModel):
    html: str

@router.put("/md", tags = ["API (Other)"], response_model = MDResponse)
async def markdown_to_html_api(request: Request, md: MDRequest):
    data = PrevRequest(html_long_description = False, data = md.markdown)
    return await preview_api(request, data)

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

@router.put("/preview", tags = ["API (Other)"], response_model = MDResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def preview_api(request: Request, data: PrevRequest):
    if not data.html_long_description:
        html = emd(markdown.markdown(data.data, extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        html = data.data
    # Take the h1...h5 anad drop it one lower
    html = html.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p").replace("<a", "<a class='long-desc-link'").replace("ajax", "").replace("http://", "https://").replace(".alert", "")
    return {"html": html}


async def ws_close(websocket: WebSocket, code: int):
    try:
        return await websocket.close(code=code)
    except:
        return

@router.websocket("/api/ws") # Compatibility, will be undocumented soon
@router.websocket("/api/ws/bot")
async def websocket_bot(websocket: WebSocket):
    await manager.connect(websocket)
    if websocket.api_token == []:
        await manager.send_personal_message({"payload": "IDENTITY", "type": "API_TOKEN"}, websocket)
        try:
            api_token = await websocket.receive_json()
            print("HERE")
            if api_token.get("payload") != "IDENTITY_RESPONSE" or api_token.get("type") != "API_TOKEN":
                raise TypeError
        except:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        api_token = api_token.get("data")
        if api_token is None or type(api_token) == int or type(api_token) == str:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        for bot in api_token:
            bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(bot))
            if bid is None:
                pass
            else:
                websocket.api_token.append(api_token)
                websocket.bot_id.append(bid["bot_id"])
        if websocket.api_token == [] or websocket.bot_id == []:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket)
            return await ws_close(websocket, 4004)
    await manager.send_personal_message({"payload": "STATUS", "type": "READY", "data": [str(bid) for bid in websocket.bot_id]}, websocket)
    try:
        asyncio.create_task(ws_send_events())
        while True:
            await asyncio.sleep(1) # Keep Waiting Forever
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@router.websocket("/api/ws/chat")
async def chat_api(websocket: WebSocket):
    await manager_chat.connect(websocket)
    if websocket.chat_token == None:
        await manager_chat.send_personal_message({"payload": "IDENTITY", "type": "CHAT_TOKEN,API_TOKEN_RECIPIENT"}, websocket)
        try:
            data = await websocket.receive_json()
            print("HERE")
            if data.get("payload") != "IDENTITY_RESPONSE" or data.get("type") not in ["CHAT_TOKEN", "API_TOKEN_RECIPIENT"]:
                raise TypeError
        except:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        if data.get("type") == "CHAT_TOKEN":
            chat_token = data.get("data")
            if chat_token is None or type(chat_token) == int:
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
                return await ws_close(websocket, 4004)
            blocked = await redis_db.hget(chat_token, key = "blocked") # Check if the user was blocked
            if blocked is None:
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid chat token provided
                return await ws_close(websocket, 4004)
            elif blocked == "global":
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "CHAT_BLOCKED"}, websocket) # User blocked
                return await ws_close(websocket, 4004)
            websocket.sender = await redis_db.hget(chat_token, key = "sender") # Get the sender
            websocket.receiver = await redis_db.hget(chat_token, key = "receiver")
            websocket.chat_token = chat_token
        elif data.get("type") == "API_TOKEN_RECIPIENT":
            api_token = data.get("data")
            if type(api_token) != list or type(api_token[0]) != str or type(api_token[1]) != str or len(api_token) > 2: # Format is user token, reciever id
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
                return await ws_close(websocket, 4004)
            sender = await db.fetchval("SELECT user_id FROM users WHERE api_token = $1", str(api_token[0]))
            if sender is None:
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid api token provided
                return await ws_close(websocket, 4004)
            sender = str(sender)
            receiver = str(api_token[1])
            ongoing_chat = await redis_db.hget(":".join([sender, receiver]), key = "ongoing")
            if ongoing_chat is not None and ongoing_chat != "":
                # Ongoing chat, tell client to transfer
                await manager_chat.send_personal_message({"payload": "TRANSFER_CONN", "type": "CHAT_TOKEN", "data": ongoing_chat.decode('utf-8')}, websocket) # Chat Transfer
                return await ws_close(websocket, 4005) # 4005 = Close
            # Create a new chat token, hand it to user and close connection
            chat_token = get_token(132)
            await redis_db.hset(chat_token, mapping = {"blocked": "", "sender": sender, "receiver": receiver})
            await redis_db.hset(":".join([sender, receiver]), key = "ongoing", value = chat_token)
            await manager_chat.send_personal_message({"payload": "TRANSFER_CONN", "type": "CHAT_TOKEN", "data": chat_token}, websocket) # Chat Transfer
            return await ws_close(websocket, 4005) # 4005 = Transfer
        await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NOT_IMPLEMENTED"}, websocket) # Chat functionality is not yet implemented
        return await ws_close(websocket, 4006) # 4006 = Not Implemented Close


class User(BaseModel):
    id: int
    desription: str

@router.get("/users/{user_id}", tags = ["API"])
async def get_user_api(request: Request, user_id: int):
    user = await db.fetchrow("SELECT description, css, user_id AS id FROM users WHERE user_id = $1", user_id)
    user_obj = await get_user(user_id)
    if user is None:
        return abort(404)
    return dict(user) | {"user": user_obj}

class ValidServer(BaseModel):
    valid: dict

@router.get("/users/{user_id}/valid_servers", tags = ["API (Internal)"], dependencies=[Depends(RateLimiter(times=3, minutes=5))], response_model = ValidServer)
async def get_valid_servers_api(request: Request, user_id: int):
    """Internal API to get users who have the FL Server Bot and Manage Server/Admin"""
    valid = {}
    request.session["valid_servers"] = []
    access_token = await discord_o.access_token_check(request.session["dscopes_str"], request.session["access_token"])
    request.session["access_token"] = access_token
    servers = await discord_o.get_guilds(access_token["access_token"], permissions = [0x8, 0x20]) # Check for all guilds with 0x8 and 0x20
    for server in servers:
        try:
            guild = client_servers.get_guild(int(server))
        except:
            guild = None
        if guild is None:
            continue
        try:
            member = guild.get_member(int(user_id))
        except:
            member = None
        if member is None:
            continue
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            valid = valid | {str(guild.id): {"icon": str(guild.icon_url), "name": guild.name, "member_count": guild.member_count, "created_at": guild.created_at}}
            request.session["valid_servers"].append(str(guild.id))
    return {"valid": valid}

class UserDescEdit(BaseModel):
    description: str

@router.patch("/users/{user_id}/description", tags = ["API"])
async def set_user_description_api(request: Request, user_id: int, desc: UserDescEdit, Authorization: str = Header("INVALID_API_TOKEN")):
    id = await db.fetchrow("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", desc.description, user_id)
    return {"done": True, "reason": None}

@router.post("/stripe/checkout", dependencies=[Depends(RateLimiter(times=6, minutes=3))], tags = ["API (Internal)"])
async def stripetest_post_api(request: Request, user_id: int, discount: Optional[str] = "GENERIC_NULL_DISCOUNT"):
    line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Coin',
                },
                'unit_amount': 50,
            },
            'adjustable_quantity': {
                'enabled': True,
                'minimum': 3,
            },
            'quantity': 3,
        }]
    metadata = {
            'user_id': user_id,
            'token': get_token(256)
        }
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            metadata=metadata,
            discounts=[{
                'coupon': f'{discount}',
            }],
            mode='payment',
            success_url='https://fateslist.xyz/fates/stripe/success',
            cancel_url='https://fateslist.xyz/fates/stripe/cancel',
        )
    except stripe.error.InvalidRequestError:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            metadata=metadata,
            mode='payment',
            success_url='https://fateslist.xyz/fates/stripe/success',
            cancel_url='https://fateslist.xyz/fates/stripe/cancel',
        )
    return {"id": session.id}

@router.post("/stripe/webhook", tags = ["API (Internal)"])
async def stripetest_post_pay_api(request: Request):
    payload = await request.body()
    sig_header = request.headers['stripe-signature']
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
    except ValueError as e:
        return abort(400)

    except stripe.error.SignatureVerificationError as e:
        return abort(400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        id = session["payment_intent"]
        lm = session["livemode"]
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=100)
        user_id = int(session["metadata"]["user_id"])
        quantity = int(line_items["data"][0]["quantity"])
        token = session["metadata"]["token"]
        # Save an order in your database, marked as 'awaiting payment'
        await create_order(user_id, quantity, token, id, lm)

        # Check if the order is already paid (e.g., from a card payment)
        #
        # A delayed notification payment will have an `unpaid` status, as
        # you're still waiting for funds to be transferred from the customer's
        # account.
        if session.payment_status == "paid":
            # Fulfill the purchase
            await fulfill_order(user_id, quantity, token, id, lm)

    elif event['type'] == 'checkout.session.async_payment_succeeded':
        session = event['data']['object']
        id = session["payment_intent"]
        lm = session["livemode"]
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=100)
        user_id = int(session["metadata"]["user_id"])
        quantity = int(line_items["data"][0]["quantity"])
        token = session["metadata"]["token"]
        # Fulfill the purchase
        await fulfill_order(user_id, quantity, token, id, lm)

    elif event['type'] == 'checkout.session.async_payment_failed':
        session = event['data']['object']

        # Send an DM to the customer asking them to retry their order
        await dm_customer_about_failed_payment(session)

async def create_order(user_id, quantity, token, id, lm):
    await db.execute("INSERT INTO user_payments (user_id, token, coins, paid, stripe_id, livemode) VALUES ($1, $2, $3, $4, $5, $6)", user_id, token, quantity, False, id, lm)
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(user_id)
        await user.send(f"You have successfully created an order for {quantity} coins! Your payment id is {id}. After stripe confirms your payment. The coins will be added to your account! DM a Fates List Admin with your payment id if you do not get the coins within an hour.")
    except:
        pass

async def fulfill_order(user_id, quantity, token, id, lm):
    await db.execute(f"UPDATE users SET coins = coins + {quantity} WHERE user_id = $1", user_id)
    await db.execute("UPDATE user_payments SET paid = $1 WHERE user_id = $2 AND token = $3", True, user_id, token) 
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(user_id)
        await user.send(f"We have successfully fulfilled an order for {quantity} coins! Your payment id is {id}. The coins have been added to your account! DM a Fates List Admin with your payment id if you did not get the coins.")
    except:
        pass

async def dm_customer_about_failed_payment(session):
    print("DM Customer: " + str(session))

