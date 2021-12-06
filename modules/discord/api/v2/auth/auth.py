from urllib.parse import unquote

from modules.core import *

from ..base import API_VERSION
from .models import (APIResponse, BaseUser, Login, LoginBan,
                     LoginInfo, LoginResponse, OAuthInfo)
import aiohttp
from config import auth_namespaces

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Auth"]
)

@router.post("/oauth", response_model = OAuthInfo)
async def get_login_link(request: Request, data: LoginInfo, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    if data.redirect:
        if not data.redirect.startswith("/") and not data.redirect.startswith("https://fateslist.xyz"):
            return api_error(
                "Invalid redirect. You may only redirect to pages on Fates List"
            )
    redirect = data.redirect if data.redirect else "/"
    url = await oauth.discord.get_auth_url(
        data.scopes,
    )
    return api_success(url = url.url, state=url.state)

@router.post("/users", response_model = LoginResponse)
async def login_user(request: Request, data: Login, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    db = worker_session.postgres

    try:
        access_token = await oauth.discord.get_access_token(data.code, data.scopes)
        userjson = await oauth.discord.get_user_json(access_token)
        if not userjson or not userjson.get("id"):
            raise ValueError("Invalid user json. Please contact Fates List Staff")
            
    except Exception as exc:
        return api_error(
            str(exc),
            banned = False
        )
    
    user_info = await db.fetchrow(
        "SELECT state, api_token, css, js_allowed, username, site_lang FROM users WHERE user_id = $1", 
        int(userjson["id"])
    )
    
    if not user_info or user_info["state"] is None:
        token = get_token(101)
        await db.execute(
            "DELETE FROM users WHERE user_id = $1", 
            int(userjson["id"])
        ) # Delete any potential existing but corrupt data

        await db.execute(
            "INSERT INTO users (id, user_id, username, api_token) VALUES ($1, $1, $2, $3)", 
            int(userjson["id"]), 
            userjson["username"], 
            token
        )

        css, state, js_allowed, site_lang = None, 0, True, "default"

    else:
        state = enums.UserState(user_info["state"])
        if state.__sitelock__:
            ban_data = bans_data[str(state.value)]
            return api_error(
                "You have been banned from Fates List",
                banned = True,
                ban = LoginBan(
                    type = ban_data["type"],
                    desc = ban_data["desc"],
                ),
                state = state,
                status_code = 403
            )
        if userjson["username"] != user_info["username"]:
            await db.execute(
                "UPDATE users SET username = $1", 
                userjson["username"]
            ) 

        token, css, state, js_allowed, site_lang = user_info["api_token"], user_info["css"] if user_info["css"] else None, state, user_info["js_allowed"], user_info["site_lang"]

    if userjson["avatar"]:
        avatar = f'https://cdn.discordapp.com/avatars/{userjson["id"]}/{userjson["avatar"]}.webp'
    else:
        _avatar_id = int(userjson['discriminator']) % 5
        avatar = f"https://cdn.discordapp.com/embed/avatars/{_avatar_id}.png"
    
    user = await get_user(int(userjson["id"]))

    if "guilds.join" in data.scopes:
        await oauth.discord.add_user_to_guild(access_token, userjson["id"], main_server, TOKEN_MAIN)

    request.session["scopes"] = orjson.dumps(data.scopes).decode("utf-8")
    request.session["access_token"] = orjson.dumps(access_token.dict()).decode("utf-8")
    request.session["user_id"] = str(userjson["id"])
    request.session["username"], request.session["avatar"] = userjson["username"], avatar
    request.session["user_token"], request.session["user_css"] = token, css
    request.session["js_allowed"], request.session["site_lang"] = js_allowed, site_lang

    return api_success(
        user = BaseUser(
            id = userjson["id"],
            username = userjson["username"],
            bot = False,
            disc = userjson["discriminator"],
            avatar = avatar,
            status = user["status"] if user else 0
        ),
        token = token,
        css = css,
        state = state,
        js_allowed = js_allowed,
        access_token = access_token,
        banned = False,
        scopes = data.scopes,
        site_lang = site_lang
    )

