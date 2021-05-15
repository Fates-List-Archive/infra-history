from ..core import *
from modules.models.bot_actions import BotAddForm, BotEditForm
router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"],
    include_in_schema = False
)

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

@router.get("/admin/add")
async def add_bot(request: Request):
    if "user_id" in request.session.keys():
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "error": None, "mode": "add"})
    else:
        return RedirectResponse("/auth/login?redirect=/bot/admin/add&pretty=to add a bot")

@router.post("/admin/add")
async def add_bot_backend(
        request: Request,
        bot: BotAddForm = Depends(BotAddForm),
    ):
    if "user_id" not in request.session.keys():
        return RedirectResponse("/auth/login?redirect=/bot/admin/add&pretty=to add a bot", status_code = 303)
    banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    bot_dict = bot.dict()
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    bot_dict["features"] = features
    bot_dict["user_id"] = request.session.get("user_id")
    bot_adder = BotActions(bot_dict)
    try:
        rc = await asyncio.shield(bot_adder.add_bot())
    except:
        rc = await asyncio.shield(bot_adder.add_bot())
    if rc is None:
        return RedirectResponse("/bot/" + str(bot_dict["bot_id"]), status_code = 303)
    bot_dict["tags"] = bot_dict["tags"].split(",")
    return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": rc[0], "code": rc[1], "mode": "add"})

@router.get("/{bot_id}/edit")
async def bot_edit(request: Request, bot_id: int, csrf_protect: CsrfProtect = Depends()):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(int(bot_id), int(request.session.get("user_id")))
        if not check:
            return abort(403)
        try:
            fetch = dict(await db.fetchrow("SELECT bot_id, prefix, bot_library AS library, invite, website, banner, long_description, description, webhook, webhook_secret, webhook_type, discord AS support, api_token, banner, github, features, long_description_type, css, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id))
        except:
            return abort(404)
        tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
        fetch = fetch | {"tags": [tag["tag"] for tag in tags]}
        owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
        logger.trace(owners)
        if owners is None:
            return "This bot has no found owners.\nPlease contact Fates List support"
        fetch = fetch | {"extra_owners": [obj["owner"] for obj in owners if obj["main"] is False]}
        if fetch["extra_owners"]:
            fetch["extra_owners"] = ",".join([str(eo) for eo in fetch["extra_owners"]])
        else:
            fetch["extra_owners"] = ""
        vanity = await db.fetchrow("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bot_id)
        if vanity is None:
            vanity = {"vanity": None}
        bot = fetch | dict(vanity)
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "mode": "edit", "tags_fixed": tags_fixed, "username": request.session.get("username", False),"data": bot, "avatar": request.session.get("avatar"), "epoch": time.time(), "vanity": vanity["vanity"], "csrf_protect": csrf_protect})
    else:
        return RedirectResponse("/")

@router.post("/{bot_id}/edit")
async def bot_edit_backend(
        request: Request,
        bot_id: int,
        bot: BotEditForm = Depends(BotEditForm),
        csrf_protect: CsrfProtect = Depends()
    ):
    ret = await verify_csrf(request, csrf_protect)
    if ret:
        return ret # CSRF
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    check = await is_bot_admin(bot_id, int(request.session.get("user_id")))
    if not check:
        return abort(403)
    banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    guild = client.get_guild(main_server)
    bot_dict = bot.dict()
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    bot_dict["features"] = features
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = request.session.get("user_id")
    bot_editor = BotActions(bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return RedirectResponse("/bot/" + str(bot_id), status_code = 303)
    bot_dict["tags"] = bot_dict["tags"].split(",")
    return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": rc[0], "code": rc[1], "mode": "edit", "csrf_protect": csrf_protect})

class RC(BaseModel):
    g_recaptcha_response: str = FForm(None)

@router.post("/{bot_id}/vote")
async def vote_for_bot_or_die(
        request: Request,
        bot_id: int,
        csrf_protect: CsrfProtect = Depends()
    ):
    ret = await verify_csrf(request, csrf_protect)
    if ret:
        return ret # CSRF
    if request.session.get("user_id") is None:
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to vote for this bot", status_code = 303)
    user_id = int(request.session.get("user_id"))
    ret = await vote_bot(user_id = user_id, username = request.session.get("username"), bot_id = bot_id, autovote = False, test = False)
    if ret == []:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully voted for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>", "username": request.session.get("username", False), "avatar": request.session.get('avatar')})
    elif ret[0] in [404, 500]:
        return abort(ret[0])
    elif ret[0] == 401:
        wait_time = round(ret[1].total_seconds())
        wait_time_hr = wait_time//(60*60)
        wait_time_mp = (wait_time - (wait_time_hr*60*60)) # Minutes
        wait_time_min = wait_time_mp//60
        wait_time_sec = (wait_time_mp - wait_time_min*60)
        if wait_time_min < 1:
            wait_time_min = 1
        if wait_time_hr == 1:
            hr = "hour"
        else:
            hr = "hours"
        if wait_time_min == 1:
            min = "minute"
        else:
            min = "minutes"
        if wait_time_sec == 1:
            sec = "second"
        else:
            sec = "seconds"
        wait_time_human = " ".join((str(wait_time_hr), hr, str(wait_time_min), min, str(wait_time_sec), sec))
        return await templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Vote Error", "context": "Please wait " + wait_time_human + " before voting for this bot"})
    else:
        return ret

@router.post("/{bot_id}/delete")
async def delete_bot(request: Request, bot_id: int):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(int(bot_id), int(request.session.get("user_id")))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database."})
        elif check == False:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only owners and admins can delete bots", "username": request.session.get("username", False)})
        await add_rmq_task("bot_delete_queue", {"user_id": int(request.session["user_id"]), "bot_id": bot_id})
    return RedirectResponse("/", status_code = 303)

@router.post("/{bot_id}/ban")
async def ban_bot(request: Request, bot_id: int, ban: int = FForm(1), reason: str = FForm('There was no reason specified')):
    guild = client.get_guild(main_server)
    if ban not in [0, 1]:
        return RedirectResponse(f"/bot/{bot_id}", status_code = 303)
    if reason == "":
        reason = "There was no reason specified"

    if "user_id" in request.session.keys():
        check = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("user_id")))
        if is_staff(staff_roles, user.roles, 3)[0]:
            pass
        else:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only owners, admins and moderators can unban bots. Please contact them if you accidentally denied a bot.", "username": request.session.get("username", False)})
    admin_tool = BotListAdmin(bot_id, int(request.session.get("user_id")))
    if ban == 1:
        await admin_tool.ban_bot(reason)
        return "Bot Banned :)"
    else:
        await admin_tool.unban_requeue_bot(check)
        return "Bot Unbanned :)"
    return RedirectResponse("/", status_code = 303)

@router.post("/{bot_id}/reviews/new")
async def new_reviews(request: Request, bot_id: int, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to review this bot", status_code = 303)
    check = await db.fetchrow("SELECT bot_id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, int(request.session["user_id"]))
    if check is not None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You have already made a review for this bot, please edit that one instead of making a new one!"})
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch) VALUES ($1, $2, $3, $4, $5, $6)", id, bot_id, int(request.session["user_id"]), rating, review, [time.time()])
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(request.session["user_id"]), "reply": False, "id": str(id), "star_rating": rating, "review": review, "root": None})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully made a review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>", "username": request.session.get("username", False), "avatar": request.session.get('avatar')}) 

@router.post("/{bot_id}/reviews/{rid}/edit")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to edit reviews", status_code = 303)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(request.session["user_id"]))
    s = is_staff(staff_roles, user.roles, 2)
    if s[0]:
        check = await db.fetchrow("SELECT epoch, reply FROM bot_reviews WHERE id = $1", rid)
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review (doesn't actually exist)"})
    else:
        check = await db.fetchrow("SELECT epoch, reply FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, int(request.session["user_id"]))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review"})
    if check["epoch"] is not None:
        check["epoch"].append(time.time())
        epoch = check["epoch"]
    else:
        epoch = [time.time()]
    await db.execute("UPDATE bot_reviews SET star_rating = $1, review_text = $2, epoch = $3 WHERE id = $4", rating, review, epoch, rid)
    await bot_add_event(bot_id, enums.APIEvents.review_edit, {"user": str(request.session["user_id"]), "id": str(rid), "star_rating": rating, "review": review, "reply": check["reply"]})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully editted your/this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.post("/{bot_id}/reviews/{rid}/reply")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to reply to reviews", status_code = 303)
    check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1", rid)
    if check is None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to reply to this review (doesn't actually exist)"})
    reply_id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch, reply) VALUES ($1, $2, $3, $4, $5, $6, $7)", reply_id, bot_id, int(request.session["user_id"]), rating, review, [time.time()], True)
    replies = check["replies"]
    replies.append(reply_id)
    await db.execute("UPDATE bot_reviews SET replies = $1 WHERE id = $2", replies, rid)
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(request.session["user_id"]), "reply": True, "id": str(reply_id), "star_rating": rating, "review": review, "root": str(rid)})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully replied to your/this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.get("/{bot_id}/resubmit")
async def resubmit_bot(request: Request, bot_id: int):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(bot_id, int(request.session.get("user_id")))
        if not check:
            return abort(403)
    else:
        return RedirectResponse("/")
    bot = await get_bot(bot_id)
    if not bot:
        return abort(404)
    return await templates.TemplateResponse("resubmit.html", {"request": request, "bot": bot, "bot_id": bot_id})

@router.post("/{bot_id}/resubmit")
async def resubmit_bot(request: Request, bot_id: int, appeal: str = FForm("No appeal provided"), qtype: str = FForm("off")):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(bot_id, int(request.session.get("user_id")))
        if not check:
            return abort(403)
    else:
        return RedirectResponse("/")
    bot = await get_bot(bot_id)
    if bot is None:
        return abort(404)
    resubmit = qtype == "on"
    reschannel = client.get_channel(appeals_channel)
    if resubmit:
        title = "Bot Resubmission"
        type = "Context"
    else:
        title = "Ban Appeal"
        type = "Appeal"
    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    resubmit_embed.add_field(name="Username", value = user['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bot_id))
    resubmit_embed.add_field(name="Resubmission", value = str(resubmit))
    resubmit_embed.add_field(name=type, value = appeal)
    await reschannel.send(embed = resubmit_embed)
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Appeal sent successfully!."})

