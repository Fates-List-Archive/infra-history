#from modules.discord.bots import vote_bot_get
#from modules.discord.servers import guild_page

from ..core import *
#from config import privacy_policy, partners
router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)

@router.get("/_sunbeam/dm/help")
async def internal_dm_help(request: Request):
    if not request.headers.get("Frostpaw"):
        return abort(404)
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

    return {"message": "Please send a screenshot of this page and send it to staff (or our support server)", "data": data}

@router.post("/fates/csp")
async def csp(request: Request):
    logger.info((await request.json()))

@router.get("/")
async def index_fend(request: Request):
    return RedirectResponse("https://fateslist.xyz", status_code=301)

@router.get("/servers")
@router.get("/server")
@router.get("/guilds")
async def server_index(request: Request):
    return RedirectResponse("https://fateslist.xyz/servers", status_code=301)

@router.get("/servers/{guild_id}/{path:path}")
@router.get("/servers/{guild_id}")
def server_redirector(guild_id: int, path: Optional[str] = None):
    return RedirectResponse(f"/server/{guild_id}/{path or ''}")

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
        return RedirectResponse(redirect or "/", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse(f"https://fateslist.xyz/frostpaw/herb?redirect={redirect or 'https://api.fateslist.xyz'}")

@router.get("/api/docs")
async def api_docs_view(request: Request):
    return RedirectResponse("https://docs.fateslist.xyz", status_code=301)
