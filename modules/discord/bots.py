from ..core import *

router = APIRouter(prefix="/bot", tags=["Bots"], include_in_schema=False)

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]


@router.get("/admin/add")
async def add_bot(request: Request, iframe: bool = False):
    if not iframe:
        return RedirectResponse("https://fateslist.xyz/frostpaw/add-bot")
    if "user_id" in request.session.keys():
        fn = "bot_add_edit.html"
        context = {
            "mode":
            "add",
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
            fn,
            {
                "request": request,
                "tags_fixed": tags_fixed,
                "features": features,
                "bot": {},
                "iframe": iframe
            },
            context=context,
            compact=False,
        )
    return RedirectResponse(
        "/fates/login?redirect=/bot/admin/add&pretty=to add a bot")


@router.get("/{bot_id}/settings")
async def bot_settings(request: Request, bot_id: int, iframe: bool = False):
    if not iframe:
        return RedirectResponse(f"https://fateslist.xyz/bot/{bot_id}/settings")
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    if "user_id" not in request.session.keys():
        return RedirectResponse(
            f"/fates/login?redirect=/bot/{bot_id}/settings&pretty=to edit this bot"
        )

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
        return "This bot has no found owners.\nPlease contact Fates List support"

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
        "bot_token":
        await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1",
                          bot_id),
        "mode":
        "edit",
        "bot_id":
        str(bot_id),
        "owners_html":
        owners_html,
        "tags": [{
            "text": tag["name"],
            "value": tag["id"]
        } for tag in tags_fixed],
        "features": [{
            "text": feature["name"],
            "value": id
        } for id, feature in features.items()],
        "votes":
        bot["votes"],
    }

    fn = "bot_add_edit.html"

    return await templates.TemplateResponse(
        fn,
        {
            "request": request,
            "tags_fixed": tags_fixed,
            "bot": bot,
            "vanity": vanity,
            "features": features,
            "iframe": iframe
        },
        context=context,
        compact=False,
    )


@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")


@router.get("/{bot_id}")
async def bot_index(request: Request,
                    bot_id: int,
                    bt: BackgroundTasks,
                    rev_page: int = 1):
    return RedirectResponse(f"https://fateslist.xyz/bot/{bot_id}",
                            status_code=301)


@router.get("/{bot_id}/reviews_html", dependencies=[Depends(id_check("bot"))])
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
