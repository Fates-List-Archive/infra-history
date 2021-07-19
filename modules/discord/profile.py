from ..core import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
async def redirect_me(request: Request, preview: bool = False, worker_session = Depends(worker_session)):
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    return await get_user_profile(
        request, 
        int(request.session.get("user_id")), 
        preview = preview, 
        worker_session = worker_session
    )

@router.get("/{user_id}")
async def profile_of_user_generic(
    request: Request,
    user_id: int, 
    preview: bool = False, 
    worker_session = Depends(worker_session)
):
    return await get_user_profile(request, user_id, preview = preview, worker_session = worker_session)

async def get_user_profile(request, user_id: int, preview: bool, worker_session):
    discord = worker_session.discord
    db = worker_session.postgres

    if not discord.up():
        return await templates.e(request, "Site is still loading...")
    
    client = discord.main
    guild = client.get_guild(main_server)
    
    viewer = guild.get_member(int(request.session.get("user_id", -1)))
    admin = is_staff(staff_roles, viewer.roles, 4)[0] if viewer else False
    
    personal = user_id == int(request.session.get("user_id", -1))

    user = await core.User(
        id = user_id, 
        db = db, 
        client = client
    ).profile()

    if not user:
        return await templates.e(request, "Profile Not Found", 404)
    
    personal = personal or admin and not preview

    context = {}
    if personal:
        context["user_id"] = str(user_id)
        context["user_token"] = await db.fetchval("SELECT api_token FROM users WHERE user_id = $1", user_id)
        context["js_allowed"] = user["profile"]["js_allowed"]

    return await templates.TemplateResponse(
        "profile.html", 
        {
            "request": request, 
            "user": user, 
            "personal": (personal or admin) and not preview, 
            "admin": admin
        },
        context = context
    )
