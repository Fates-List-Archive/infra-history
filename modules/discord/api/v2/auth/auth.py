
import itsdangerous
from modules.core import *

from ..base import API_VERSION
from .models import (BaseUser, Login, LoginBan,
                     LoginInfo, LoginResponse, OAuthInfo)
from itsdangerous import URLSafeSerializer
from fastapi import Response
import base64

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Auth"]
)

@router.post("/oauth", response_model = OAuthInfo)
async def get_login_link(request: Request, data: LoginInfo, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    url = await oauth.discord.get_auth_url(
        data.scopes,
    )

    # Workaround for sunbeam
    if request.headers.get("Frostpaw"):
        url.url = url.url.replace("https://fateslist.xyz", request.headers.get("Frostpaw-Server", "https://sunbeam.fateslist.xyz")).replace("/static/login-finish.html", "/frostpaw/login", 1)
    else:
        return api_error("Unsupported auth method")

    return api_success(url = url.url, state=url.state)

@router.post("/users", response_model = LoginResponse)
async def login_user(request: Request, response: Response, data: Login, worker_session = Depends(worker_session)):
    """
    Returns a cookie containing login information
    """
    oauth = worker_session.oauth
    db = worker_session.postgres

    try:
        if request.headers.get("Frostpaw"):
            override_redirect_uri = f"{request.headers.get('Origin', 'https://sunbeam.fateslist.xyz')}/frostpaw/login"
        else:
            override_redirect_uri = "https://api.fateslist.xyz/static/login-finish.html"
        access_token = await oauth.discord.get_access_token(data.code, data.scopes, override_redirect_uri=override_redirect_uri)
        userjson = await oauth.discord.get_user_json(access_token)
        if not userjson or not userjson.get("id"):
            raise ValueError("Invalid user json. Please contact Fates List Staff")
        
    except Exception as exc:
        return api_error(
            str(exc),
            banned = False
        )
    
    user_info = await db.fetchrow(
        "SELECT state, api_token, user_css AS css, js_allowed, username, site_lang FROM users WHERE user_id = $1", 
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
                "UPDATE users SET username = $1 WHERE user_id = $2", 
                userjson["username"],
                int(userjson["id"])
            ) 

        token, css, state, js_allowed, site_lang = user_info["api_token"], user_info["css"] if user_info["css"] else None, state, user_info["js_allowed"], user_info["site_lang"]

    if userjson["avatar"]:
        avatar = f'https://cdn.discordapp.com/avatars/{userjson["id"]}/{userjson["avatar"]}.webp'
    else:
        _avatar_id = int(userjson['discriminator']) % 5
        avatar = f"https://cdn.discordapp.com/embed/avatars/{_avatar_id}.png"
    
    user = await get_user(int(userjson["id"]), worker_session=worker_session)

    if "guilds.join" in data.scopes:
        await oauth.discord.add_user_to_guild(access_token, userjson["id"], main_server, TOKEN_MAIN)

    user = BaseUser(
        id = userjson["id"],
        username = userjson["username"],
        bot = False,
        disc = userjson["discriminator"],
        avatar = avatar,
        status = user["status"] if user else 0
    )

    if request.headers.get("Frostpaw"):
        login_token_tss = orjson.dumps({"token": token, "user": user.dict(), "site_lang": site_lang, "css": css})

        response.set_cookie(
            key="sunbeam-session:warriorcats", 
            value=base64.b64encode(login_token_tss).decode(), 
            max_age=60*60*8, 
            httponly=True, 
            samesite="strict", 
            secure=True,
            domain="fateslist.xyz",
            path="/"
        )

    return {
        "done": True,
        "reason": None,
        "state": state,
        "banned": False,
    }

@router.post("/logout/_sunbeam")
def logout_sunbeam(request: Request, response: Response):
    if not request.headers.get("Frostpaw"):
        return abort(404)
    
    response.set_cookie(
        key="sunbeam-key", 
        value="0", 
        expires="Thu, 01 Jan 1970 00:00:00 GMT", 
        httponly=True, 
        samesite="lax", 
        secure=True,
        domain="fateslist.xyz",
        path="/"
    )

    response.set_cookie(
        key="sunbeam-session:warriorcats", 
        value="0", 
        expires="Thu, 01 Jan 1970 00:00:00 GMT", 
        httponly=True, 
        samesite="lax", 
        secure=True,
        domain="fateslist.xyz",
        path="/"
    )

    return {}
