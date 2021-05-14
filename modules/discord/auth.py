from ..core import *

router = APIRouter(
    prefix = "/auth",
    tags = ["Auth"],
    include_in_schema = False
)

discord_o = Oauth(OauthConfig)

@router.get("/login")
async def login_get(request: Request, redirect: Optional[str] = None, pretty: Optional[str] = "to access this page", csrf_protect: CsrfProtect = Depends()):
    if redirect:
        if not redirect.startswith("/") and not redirect.startswith("https://fateslist.xyz"):
            return ORJSONResponse({"detail": "Invalid redirect. You may only redirect to pages on Fates List"}, status_code = 400)
    if "userid" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    request.session["redirect"] = redirect
    return await templates.TemplateResponse("login.html", {"request": request, "perm_needed": redirect is not None, "perm_pretty": pretty, "csrf_protect": csrf_protect})

@router.post("/login")
async def login_post(request: Request, join_servers: str = FForm("off"), server_list: str = FForm("off"), csrf_protect: CsrfProtect = Depends()):
    verify_csrf(request, csrf_protect)
    scopes = ["identify"]

    # Join Server
    if join_servers == "off":
        request.session["join_servers"] = False
    else:
        request.session["join_servers"] = True
        scopes.append("guilds.join")

    # Server Lists
    if server_list == "off":
        request.session["server_list"] = False
    else:
        request.session["server_list"] = True
        scopes.append("guilds")
    oauth_data = discord_o.get_discord_oauth(scopes)
    return RedirectResponse(oauth_data["url"], status_code=HTTP_303_SEE_OTHER)

@router.get("/login/confirm")
async def login_confirm(request: Request, code: str, state: str):
    if "userid" in request.session.keys():
        return RedirectResponse("/")
    else:
        access_token = await discord_o.get_access_token(code, state)
        userjson = await discord_o.get_user_json(access_token["access_token"])
        if userjson["id"]:
            pass
        else:
            return RedirectResponse("/")
        state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", int(userjson["id"]))
        if state is None:
            state = enums.UserState.normal
        ban_data = bans_data.get(str(state))
        if ban_data is None:
            ban_data = {"type": "", "desc": ""}
        if state in [enums.UserState.global_ban, enums.UserState.login_ban, enums.UserState.ddr_ban]: # 1 = Global ban, 2 = Login Ban, 4 = DDR Ban
            ban_type = ban_data["type"]
            return await templates.e(request, f"You have been {ban_type} banned from Fates List<br/>", status_code = 403)
        request.session["ban"] = state
        request.session["access_token"] = access_token
        request.session["userid"] = userjson["id"]
        logger.debug(f"Got user json of {userjson}")
        request.session["username"] = str(userjson["name"])
        if (userjson.get("avatar")):
            logger.trace(f"Got avatar {userjson.get('avatar')}")
            request.session["avatar"] = "https://cdn.discordapp.com/avatars/" + \
                userjson["id"] + "/" + userjson["avatar"]
        else:
            # No avatar in user
            request.session["avatar"] = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"
        # 794834630942654546
        token = await get_user_token(int(userjson["id"]), request.session.get("username"))
        request.session["user_token"] = token
        user_css = await db.fetchrow("SELECT css FROM users WHERE user_id = $1", int(request.session["userid"]))
        if user_css is None:
            request.session["user_css"] = ""
        else:
            request.session["user_css"] = user_css["css"]
        if request.session.get("join_servers"):
            await discord_o.join_user(access_token["access_token"], userjson["id"])
        if request.session.get("redirect") is not None:
            return RedirectResponse(request.session["redirect"])
        request.session["ban_data"] = ban_data
        if state != 0:
            ban_type = ban_data["type"]
            ban_desc = ban_data["desc"]
            return await templates.e(request, main = f"<span style='color: red;'>You have been {ban_type} banned in Fates List.</span>", reason = f"You can still login however {ban_desc}. Click 'Go Back Home' to finish logging in.", status_code = 200)
        return RedirectResponse("/")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
