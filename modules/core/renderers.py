"""
Handles rendering of bots, index, search and profile search etc.
"""
from lxml.html.clean import Cleaner

from .events import *
from .helpers import *
from .imports import *
from .permissions import *
from .templating import *

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

def gen_owner_html(owners_lst: tuple):
    owners_html = '<span class="iconify" data-icon="mdi-crown" data-inline="false" data-height="1.5em" style="margin-right: 3px"></span>'
    owners_html += "<br/>".join([f"<a class='long-desc-link' href='/profile/{owner[0]}'>{owner[1]}</a>" for owner in owners_lst if owner])
    return owners_html

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

