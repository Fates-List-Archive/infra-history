from ..core import *

router = APIRouter(tags=["Sunbeam - Internal HTML Routes"])

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

@router.get("/_sunbeam/dm/help")
async def troubleshoot_api(request: Request):
    """
    Internal API used by sunbeam for troubleshooting issues

    Used in https://fateslist.xyz/frostpaw/troubleshoot

    This requires a Frostpaw header to be properly set
    """
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

@router.post("/_sunbeam/pub/csp")
async def csp_report(request: Request):
    """
    This is where CSP reports should be sent to.

    CSP reports should not happen in practice.

    **These requests are logged to loguru**
    """
    try:
        logger.warning("CSP Report: ", (await request.json()))
    except:
        pass
    return api_success()

@router.get("/_sunbeam/pub/stats")
async def stats_page(request: Request, full: bool = False):
    """Our statistics page"""
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

@router.get("/_sunbeam/pub/add-bot")
async def add_bot(request: Request):
    if "user_id" not in request.session.keys():
        return abort(404)

    context = {
        "mode": "add",
        "tags": [{
            "text": tag["name"],
            "value": tag["id"]
        } for tag in tags_fixed],
        "features": [{
            "text": feature["name"],
            "value": id
        } for id, feature in features.items()],
    }
    return await templates.TemplateResponse(
        "bot_add_edit.html",
        {
            "request": request,
            "tags_fixed": tags_fixed,
            "features": features,
            "bot": {},
            "iframe": True
        },
        context=context,
        compact=False,
    )

@router.get("/_sunbeam/pub/bot/{bot_id}/settings")
async def bot_settings(request: Request, bot_id: int):
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    if "user_id" not in request.session.keys():
        return abort(400)

    check = await is_bot_admin(bot_id, int(request.session["user_id"]))
    if (not check and bot_id !=
            798951566634778641):  # Fates list main bot is staff viewable
        return await templates.e(request,
                                 "You are not allowed to edit this bot!",
                                 status_code=403)

    bot = await db.fetchrow(
        "SELECT bot_id, client_id, state, prefix, votes, bot_library AS library, invite, website, banner_card, banner_page, long_description, description, webhook, webhook_secret, webhook_type, discord AS support, flags, github, features, long_description_type, css, donate, privacy_policy, nsfw, keep_banner_decor FROM bots WHERE bot_id = $1",
        bot_id,
    )
    if not bot:
        return abort(404)

    bot = dict(bot)

    # Will be removed once discord becomes de-facto platform
    bot["platform"] = "discord"

    if flags_check(bot["flags"], enums.BotFlag.system):
        bot["system_bot"] = True
    else:
        bot["system_bot"] = False

    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    bot["tags"] = [tag["tag"] for tag in tags]
    owners = await db.fetch(
        "SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
    if not owners:
        return await templates.e(request,
            "Invalid owners set. Contact Fates List Support",
            status_code=400)
    owners_lst = [(await get_user(obj["owner"],
                                  user_only=True,
                                  worker_session=worker_session))
                  for obj in owners
                  if obj["owner"] is not None and obj["main"]]

    owners_lst_extra = [(await get_user(obj["owner"],
                                        user_only=True,
                                        worker_session=worker_session))
                        for obj in owners
                        if obj["owner"] is not None and not obj["main"]]

    owners_html = gen_owner_html(owners_lst + owners_lst_extra)

    bot["extra_owners"] = ",".join(
        [str(o["owner"]) for o in owners if not o["main"]])
    bot["user"] = await get_bot(bot_id, worker_session=worker_session)
    if not bot["user"]:
        return abort(404)

    vanity = await db.fetchval(
        "SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bot_id)
    bot["vanity"] = vanity
    context = {
        "bot_token": await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1", bot_id),
        "mode": "edit",
        "bot_id": str(bot_id),
        "owners_html": owners_html,
        "tags": [{
            "text": tag["name"],
            "value": tag["id"]
        } for tag in tags_fixed],
        "features": [{
            "text": feature["name"],
            "value": id
        } for id, feature in features.items()],
        "votes": bot["votes"],
    }

    return await templates.TemplateResponse(
        "bot_add_edit.html",
        {
            "request": request,
            "tags_fixed": tags_fixed,
            "bot": bot,
            "vanity": vanity,
            "features": features,
            "iframe": True
        },
        context=context,
        compact=False,
    )

@router.get("/_sunbeam/pub/bot/{bot_id}/reviews_html", dependencies=[Depends(id_check("bot"))])
async def bot_review_page(request: Request,
                          bot_id: int,
                          page: int = 1,
                          user_id: int | None = 0):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session,
                                  bot_id,
                                  page=page)
    context = {
        "id": str(bot_id),
        "type": "bot",
        "reviews": {
            "average_rating": float(reviews[1])
        },
        "user_id": str(user_id),
    }
    data = {
        "bot_reviews": reviews[0],
        "average_rating": reviews[1],
        "total_reviews": reviews[2],
        "review_page": page,
        "total_review_pages": reviews[3],
        "per_page": reviews[4],
    }

    bot_info = await get_bot(bot_id,
                             worker_session=request.app.state.worker_session)
    if bot_info:
        user = dict(bot_info)
        user["name"] = user["username"]

    else:
        return await templates.e(request, "Bot Not Found")

    return await templates.TemplateResponse(
        "ext/reviews.html",
        {
            "request": request,
            "data": {
                "user": user
            }
        } | data,
        context=context,
    )

@router.get("/_sunbeam/pub/server/{guild_id}/reviews_html")
async def guild_review_page(request: Request, guild_id: int, page: int = 1):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session, guild_id, page=page, target_type=enums.ReviewType.server)
    context = {
        "id": str(guild_id),
        "type": "server",
        "reviews": {
            "average_rating": float(reviews[1])
        },
        "index": "/servers"
    }
    data = {
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4],
    }

    user = {}
    
    return await templates.TemplateResponse("ext/reviews.html", {"request": request, "data": {"user": user}} | data, context = context)

@router.get("/_sunbeam/pub/profile/{user_id}/settings")
async def profile_editor(
    request: Request,
    user_id: int,
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
    return await templates.TemplateResponse("profile_edit.html", {"request": request, "iframe": True} | context, context=context)

