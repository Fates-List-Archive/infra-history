from ..core import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"],
    include_in_schema = False
)

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

@router.get("/admin/add")
async def add_bot(request: Request):
    if "user_id" in request.session.keys():
        fn = "bot_add_edit.html"
        context = {
            "mode": "add",
            "tags": [{"text": tag["name"], "value": tag["id"]} for tag in tags_fixed],
            "features": [{"text": feature["name"], "value": id} for id, feature in features.items()]
        }
        return await templates.TemplateResponse(fn, {"request": request, "tags_fixed": tags_fixed, "features": features, "bot": {}}, context = context)
    else:
        return RedirectResponse("/fates/login?redirect=/bot/admin/add&pretty=to add a bot")

@router.get("/{bot_id}/settings")
async def bot_settings(request: Request, bot_id: int):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/fates/login?redirect=/bot/{bot_id}/settings&pretty=to edit this bot")
    
    check = await is_bot_admin(bot_id, int(request.session["user_id"]))
    if not check and bot_id != 798951566634778641: # Fates list main bot is staff viewable
        return abort(403)
    
    bot = await db.fetchrow(
        "SELECT bot_id, client_id, state, prefix, bot_library AS library, invite, website, banner_card, banner_page, long_description, description, webhook, webhook_secret, webhook_type, discord AS support, github, features, long_description_type, css, donate, privacy_policy, nsfw, keep_banner_decor FROM bots WHERE bot_id = $1", 
        bot_id
    )
    if not bot:
        return abort(404)
    
    bot = dict(bot)
    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    bot["tags"] = [tag["tag"] for tag in tags]
    owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
    if not owners:
        return "This bot has no found owners.\nPlease contact Fates List support"
    
    owners_lst = [
        (await get_user(obj["owner"], user_only = True, worker_session = worker_session))
        for obj in owners if obj["owner"] is not None and obj["main"]
    ]

    owners_lst_extra = [
        (await get_user(obj["owner"], user_only = True, worker_session = worker_session))
        for obj in owners if obj["owner"] is not None and not obj["main"]
    ]
    
    owners_html = gen_owner_html(owners_lst + owners_lst_extra)   
        
    bot["extra_owners"] = ",".join([str(o["owner"]) for o in owners if not o["main"]])
    bot["user"] = await get_bot(bot_id, worker_session = worker_session)
    if not bot["user"]:
        return abort(404)

    vanity = await db.fetchval("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bot_id)
    bot["vanity"] = vanity
    context = {
        "bot_token": await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1", bot_id),
        "mode": "edit",
        "bot_id": str(bot_id),
        "owners_html": owners_html,
        "tags": [{"text": tag["name"], "value": tag["id"]} for tag in tags_fixed],
        "features": [{"text": feature["name"], "value": id} for id, feature in features.items()]
    }
    
    fn = "bot_add_edit.html"

    return await templates.TemplateResponse(fn, {"request": request, "tags_fixed": tags_fixed, "bot": bot, "vanity": vanity, "features": features}, context = context)
