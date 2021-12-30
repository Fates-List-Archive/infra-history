"""
Handles rendering of bots, index, search and profile search etc.
"""

import bleach
import markdown
from lxml.html.clean import Cleaner

from .events import *
from .helpers import *
from .imports import *
from .permissions import *
from .templating import *
from modules.models import constants

cleaner = Cleaner()

async def render_index(request: Request, api: bool, type: enums.ReviewType = enums.ReviewType.bot):
    worker_session = request.app.state.worker_session
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

    if not api:
        return await templates.TemplateResponse("index.html", {"request": request, "random": random} | context | base_json, context = context)
    return base_json

#@jit(nopython = True)
def gen_owner_html(owners_lst: tuple):
    """Generate the owner html"""
    # First owner will always be main and hence should have the crown, set initial state to crown for that
    owners_html = '<span class="iconify" data-icon="mdi-crown" data-inline="false" data-height="1.5em" style="margin-right: 3px"></span>'
    owners_html += "<br/>".join([f"<a class='long-desc-link' href='/profile/{owner[0]}'>{owner[1]}</a>" for owner in owners_lst if owner])
    return owners_html

async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, api: bool, rev_page: int = 1):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis
    if bot_id >= 9223372036854775807: # Max size of bigint
        return abort(404)
    
    BOT_CACHE_VER = 1

    bot_cache = await redis.get(f"botpagecache:{bot_id}")
    use_cache = True
    if not bot_cache:
        use_cache = False
    else:
        bot_cache = orjson.loads(bot_cache)
        if bot_cache.get("fl_cache_ver") != BOT_CACHE_VER:
            use_cache = False
    
    if not use_cache:
        logger.info("Using cache for new bot request")
        bot = await db.fetchrow(
            """SELECT bot_id, prefix, shard_count, state, description, bot_library AS library, 
            website, votes, guild_count, discord AS support, banner_page AS banner, github, features, 
            invite_amount, css, long_description_type, long_description, donate, privacy_policy, 
            nsfw, keep_banner_decor, flags, last_stats_post, created_at FROM bots WHERE bot_id = $1 OR client_id = $1""", 
            bot_id
        )
        if not bot:
            return abort(404)
        bot_id = bot["bot_id"]
        _resources = await db.fetch("SELECT id, resource_title, resource_link, resource_description FROM resources WHERE target_id = $1 AND target_type = $2", bot_id, enums.ReviewType.bot.value)
        resources = []

        # Bypass for UUID issue
        for resource in _resources:
            resource_dat = dict(resource)
            resource_dat["id"] = str(resource_dat["id"])
            resources.append(resource_dat)

        tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
        if not tags:
            return abort(404)

        bot = dict(bot) | {"tags": [tag["tag"] for tag in tags], "resources": resources}
        
        # Ensure bot banner_page is disable if not approved or certified
        if bot["state"] not in (enums.BotState.approved, enums.BotState.certified):
            bot["banner"] = None

        # Get all bot owners
        if flags_check(bot["flags"], enums.BotFlag.system):
            owners = await db.fetch("SELECT DISTINCT ON (owner) owner, main FROM bot_owner WHERE bot_id = $1 AND main = true", bot_id)
            bot["system"] = True
        else:
            owners = await db.fetch(
                "SELECT DISTINCT ON (owner) owner, main FROM bot_owner WHERE bot_id = $1 ORDER BY owner, main DESC", 
                bot_id
            )
            bot["system"] = False
        _owners = []
        for owner in owners:
            if owner["main"]: _owners.insert(0, owner)
            else: _owners.append(owner)
        owners = _owners
        bot["description"] = bleach.clean(ireplacem(constants.long_desc_replace_tuple, bot["description"]), strip=True, tags=["fl-lang"], attributes={"*": ["code"]})
        if bot["long_description_type"] == enums.LongDescType.markdown_pymarkdown: # If we are using markdown
            bot["long_description"] = emd(markdown.markdown(bot['long_description'], extensions = md_extensions))


        def _style_combine(s: str) -> list:
            """
            Given margin/padding, this returns margin, margin-left, margin-right, margin-top, margin-bottom etc.
            """
            return [s, s+"-left", s+"-right", s+"-top", s+"-bottom"]

        bot["long_description"] = bleach.clean(
            bot["long_description"], 
            tags=bleach.sanitizer.ALLOWED_TAGS+["span", "img", "iframe", "style", "p", "br", "center", "div", "h1", "h2", "h3", "h4", "h5", "section", "article", "fl-lang"], 
            strip=True, 
            attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES | {
                "iframe": ["src", "height", "width"], 
                "img": ["src", "alt", "width", "height", "crossorigin", "referrerpolicy", "sizes", "srcset"],
                "*": ["id", "class", "style", "data-src", "data-background-image", "data-background-image-set", "data-background-delimiter", "data-icon", "data-inline", "data-height", "code"]
            },
            styles=["color", "background", "background-color", "font-weight", "font-size"] + _style_combine("margin") + _style_combine("padding")
        )

        # Take the h1...h5 anad drop it one lower and bypass peoples stupidity 
        # and some nice patches to the site to improve accessibility
        bot["long_description"] = ireplacem(constants.long_desc_replace_tuple, bot["long_description"])

        if bot["banner"]:
            bot["banner"] = bot["banner"].replace(" ", "%20").replace("\n", "")

        bot_info = await get_bot(bot_id, worker_session = worker_session)
        
        owners_lst = [
            (await get_user(obj["owner"], user_only = True, worker_session = worker_session)) 
            for obj in owners if obj["owner"] is not None
        ]
        owners_html = gen_owner_html(owners_lst)
        if bot["features"] is not None:
            bot["features"] = "<br/>".join([f"<a class='long-desc-link' href='/feature/{feature}'>{features[feature]['name']}</a>" for feature in bot["features"]])

        bot_extra = {
            "owners_html": owners_html, 
            "user": bot_info, 
        }
        bot |= bot_extra
        
        if not bot_info:
            return await templates.e(request, "Bot Not Found")
        
        _tags_fixed_bot = [tag for tag in tags_fixed if tag["id"] in bot["tags"]]

        bot_cache = {
            "fl_cache_ver": BOT_CACHE_VER,
            "data": bot,
            "tags_fixed": _tags_fixed_bot,
        }

        # Only cache for bots with more than 1000 votes
        if bot["votes"] > 1000:
            await redis.set(f"botpagecache:{bot_id}", orjson.dumps(bot_cache), ex=60*60*4)

    bt.add_task(add_ws_event, bot_id, {"m": {"e": enums.APIEvents.bot_view}, "ctx": {"user": request.session.get('user_id'), "widget": False}})
    
    context = {
        "id": str(bot_id),
        "type": "bot",
        "replace_list": constants.long_desc_replace_tuple
    }
    
    data = bot_cache | {
        "type": "bot", 
        "id": bot_id, 
        "botp": True,
        "promos": await get_promotions(bot_id),
    }

    return await templates.TemplateResponse("bot_server.html", {"request": request, "replace_last": replace_last} | data, context = context)

async def render_search(request: Request, q: str, api: bool, target_type: enums.SearchType = enums.SearchType.bot):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    
    if q == "":
        if api:
            return abort(404)
        return RedirectResponse("/")

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
        return await render_profile_search(request, q=q, api=api)
    search_bots = await parse_index_query(
        worker_session,
        data,
        type=enums.ReviewType.bot if target_type == enums.SearchType.bot else enums.ReviewType.server
    )
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "search_bots": search_bots, "tags_fixed": tags, "query": q, "profile_search": target_type == enums.SearchType.profile, "type": "bot" if target_type == enums.SearchType.bot else "server"})
    return {"search_res": search_bots, "tags_fixed": tags, "query": q, "profile_search": target_type == enums.SearchType.profile}

async def render_profile_search(request: Request, q: str, api: bool):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    
    if q == "" or q is None:
        if api:
            return abort(404)
        q = ""
    if q.replace(" ", "") != "":
        profiles = await db.fetch(
            """SELECT DISTINCT users.user_id, users.description FROM users 
            INNER JOIN bot_owner ON users.user_id = bot_owner.owner 
            INNER JOIN bots ON bot_owner.bot_id = bots.bot_id 
            WHERE ((bots.state = 0 OR bots.state = 6) 
            AND (bots.username_cached ilike $1 OR bots.description ilike $1 OR bots.bot_id::text ilike $1)) 
            OR (users.username ilike $1) LIMIT 12""", 
            f'%{q}%'
        )
    else:
        profiles = []
    profile_obj = []
    for profile in profiles:
        profile_info = await get_user(profile["user_id"], worker_session = worker_session)
        if profile_info:
            profile_obj.append({"banner": None, "description": profile["description"], "user": profile_info})
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "tags_fixed": tags_fixed, "profile_search": True, "query": q, "type": "profile", "profiles": profile_obj})
    return {"search_res": profile_obj, "tags_fixed": tags_fixed, "query": q, "profile_search": True}

