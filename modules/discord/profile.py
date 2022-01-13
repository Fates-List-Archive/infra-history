from ..core import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/{user_id}")
async def profile_of_user_generic(
    request: Request,
    user_id: int, 
):
    return RedirectResponse(f"https://fateslist.xyz/profile/{user_id}")

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
        "bot": dict(profile) | profile["profile"],
        "langs": [{"value": lang.value, "text": lang.__doc__} for lang in list(enums.SiteLang)]
    }
    return await templates.TemplateResponse("profile_edit.html", {"request": request} | context, context=context)

