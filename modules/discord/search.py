from ..core import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"],
    include_in_schema = False
)

#@router.get("/t")
#async def search(request: Request, q: str, target_type: enums.SearchType):
#    return await render_search(request = request, q = q, api = False, target_type=target_type)

#@router.get("/tags")
#async def tags(request: Request, tag: str, target_type: enums.SearchType):
#    if target_type == enums.SearchType.bot:
#        fetch = await db.fetch("SELECT DISTINCT bots.bot_id, bots.description, bots.state, bots.banner_card AS banner, bots.votes, bots.guild_count FROM bots INNER JOIN bot_tags ON bot_tags.bot_id = bots.bot_id WHERE bot_tags.tag = $1 AND (bots.state = 0 OR bots.state = 6) ORDER BY bots.votes DESC LIMIT 15", tag)
#        tags = tags_fixed # Gotta love python
#    else:
#        fetch = await db.fetch("SELECT DISTINCT guild_id, description, state, banner_card AS banner, votes, guild_count FROM servers WHERE state = 0 AND tags && $1", [tag])
#        tags = await db.fetch("SELECT DISTINCT id, name, iconify_data FROM server_tags")
#    search_bots = await parse_index_query(request.app.state.worker_session, fetch, type=enums.ReviewType.bot if target_type == enums.SearchType.bot else enums.ReviewType.server)
#    return await templates.TemplateResponse("search.html", {"request": request, "search_bots": search_bots, "tags_fixed": tags, "profile_search": False, "type": target_type.name})

#@router.get("/profile")
#async def profile_search(request: Request, q: Optional[str] = None):
#    return await render_profile_search(request = request, q = q, api = False)
