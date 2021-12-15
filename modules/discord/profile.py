from ..core import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
async def redirect_me(request: Request, preview: bool = False, worker_session = Depends(worker_session)):
    if "user_id" not in request.session.keys():
        return abort(404)
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

@router.get("/{user_id}/edit")
async def profile_editor(
    request: Request,
    user_id: int
):
    viewer = int(request.session.get("user_id", -1))
    admin = (await is_staff(staff_roles, viewer, 4))[0] if viewer else False
    personal = user_id == int(request.session.get("user_id", -1))
    personal = personal or admin

    if not personal:
        return abort(403)

    # To profile editor, all users are bots due to prior design choices
    profile = await core_classes.User(id = user_id, db = db).profile(bot_logs = False)
    context = {
        "real_user_token": await db.fetchval("SELECT api_token FROM users WHERE user_id = $1", user_id),
        "mode": "edit",
        "bot": dict(profile) | profile["profile"]
    }
    return await templates.TemplateResponse("profile_edit.html", {"request": request} | context, context=context)

async def get_user_profile(request, user_id: int, preview: bool, worker_session):
    db = worker_session.postgres

    viewer = int(request.session.get("user_id", -1))
    admin = (await is_staff(staff_roles, viewer, 4))[0] if viewer else False
    
    personal = user_id == int(request.session.get("user_id", -1))

    user = await core_classes.User(
        id = user_id, 
        db = db, 
    ).profile(system_bots = personal)

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
            "admin": admin,
            "staff_action_get": lambda action: [obj for obj in user["profile"]["bot_logs"] if obj["action"] == action]
        },
        context = context
    )
