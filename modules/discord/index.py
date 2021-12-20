from modules.discord.bots import vote_bot_get
from modules.discord.servers import guild_page

from ..core import *
from config import privacy_policy, partners
router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)

@router.get("/dm/help")
async def exp1(request: Request):
    data = {
        "user_id": request.session.get("user_id"), 
        "logged_in": "user_id" in request.session.keys(),
        "vote_epoch": None,
        "user_agent": request.headers.get("User-Agent"),
        "user": None,
        "pid": os.getpid(),
        "ip": request.headers.get("X-Forwarded-For")
    }

    if data["logged_in"]:
        data["user"] = await get_user(data["user_id"], worker_session=request.app.state.worker_session)

    return PrettyJSONResponse({"message": "Please send a screenshot of this page and send it", "data": data})


@router.get("/fates/banappeal")
async def ban_appeal(request: Request, token: str):
    redis = request.app.state.worker_session.redis
    data = await redis.get(token)
    if not data:
        return await templates.e(request, "Invalid ban token, try logging in again!")
    return "Coming soon"

# We want to handle any request method to index page.
# cert = certified bots
@router.get("/")
@router.head("/")
async def index_fend(request: Request):
    return await render_index(request = request, api = False)

@router.get("/servers")
@router.head("/servers")
@router.get("/server")
@router.head("/server")
@router.get("/guilds")
@router.head("/guilds")
async def server_index(request: Request):
    return await render_index(request = request, api = False, type=enums.ReviewType.server)

@router.get("/servers/{guild_id}/{path:path}")
@router.get("/servers/{guild_id}")
def server_redirector(guild_id: int, path: Optional[str] = None):
    return RedirectResponse(f"/server/{guild_id}/{path or ''}")

@router.get("/etest/{code}")
async def test_error(code: int):
    if code == 500:
        b = 1 + thisshoulderror
        raise TypeError("Test 500")
    return abort(code)

@router.get("/none")
async def nonerouter():
    return RedirectResponse("/static/assets/img/banner.webp", status_code = 301)

@router.get("/{vanity}")
async def vanity_bot_uri(request: Request, bt: BackgroundTasks, vanity: str, redirect: bool = False):
    return await vanity_redirector(request, vanity, render_bot, {"bt": bt, "api": False}, guild_page)

@router.get("/{vanity}/vote")
async def vanity_vote(request: Request, vanity: str):
    return await vanity_redirector(request, vanity, vote_bot_get)

@router.get("/{vanity}/invite")
async def vanity_invite(request: Request, vanity: str):
    return await vanity_redirector(request, vanity, "invite")

@router.get("/feature/{name}")
async def features_view(request: Request, name: str):
    if name not in features.keys():
        return abort(404)
    bots = await db.fetch("SELECT description, banner_card AS banner, votes, guild_count, bot_id, invite, state FROM bots, unnest(features) feature WHERE feature = $1 and (state = 0 or state = 6) ORDER BY votes DESC LIMIT 12", name)
    bot_obj = await parse_index_query(request.app.state.worker_session, bots)
    return await templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})


@router.get("/fates/stats")
async def stats_page(request: Request, full: bool = False):
    worker_session = request.app.state.worker_session
    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    if full:
        denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
        banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    data = {
        "certified": certified,
        "bot_amount": bot_amount,
        "queue": queue,
        "denied": denied if full else [],
        "denied_amt": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.denied),
        "banned": banned if full else [],
        "banned_amt": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.banned),
        "under_review": under_review,
        "full": full
    }
    return await templates.TemplateResponse("admin.html", {"request": request} | data) # Otherwise, render the template

@router.get("/fates/login")
async def login_get(request: Request, redirect: Optional[str] = None, pretty: Optional[str] = "to access this page"):
    if "user_id" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return await templates.TemplateResponse(
            "login.html", 
            {
                "request": request
            }, 
            context = {
                "perm_needed": redirect is not None, 
                "perm_pretty": pretty, 
                "redirect": redirect if redirect else None,
                "login_page": True
            }
    )

@router.get("/fates/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/api/docs")
async def api_docs_view(request: Request):
    return RedirectResponse("https://apidocs.fateslist.xyz")

@router.get("/fates/tos")
async def tos_page(request: Request):
    return await templates.TemplateResponse("tos.html", {"request": request, "policy": privacy_policy})

@router.get("/fates/rules")
async def rules_page(request: Request):
    return await templates.TemplateResponse("rules.html", {"request": request, "policy": rules})

@router.get("/fates/partners")
async def fates_partners(request: Request):
    return await templates.TemplateResponse("partners.html", {"request": request, "partners": partners})
