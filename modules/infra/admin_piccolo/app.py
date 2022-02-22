from base64 import b64decode
from os import abort
import random
import sys
import asyncpg
import asyncio
from http import HTTPStatus

from modules.core.auth import is_staff
sys.path.append(".")
sys.path.append("modules/infra/admin_piccolo")
from fastapi import FastAPI
from typing import Callable, Awaitable, Tuple, Dict, List
from starlette.responses import Response, StreamingResponse, RedirectResponse, HTMLResponse
from starlette.requests import Request
from starlette.concurrency import iterate_in_threadpool
from fastapi.responses import ORJSONResponse
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount
from starlette.types import Scope, Message
from tables import Bot, Reviews, BotTag, User, Vanity, BotListTags, ServerTags, BotPack, BotCommand, LeaveOfAbsence, UserBotLogs
import orjson
import aioredis
from modules.core import redis_ipc_new
from config import bot_logs
from discord import Embed
from piccolo.apps.user.tables import BaseUser
from lynxfall.utils.string import get_token

admin = create_admin(
    [LeaveOfAbsence, Vanity, User, Bot, BotPack, BotCommand, BotTag, BotListTags, ServerTags, Reviews, UserBotLogs], 
    allowed_hosts = ["lynx.fateslist.xyz"], 
    production = True,
)

class Unknown:
    username = "Unknown"

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.cookies.get("sunbeam-session:warriorcats"):
            request.scope["sunbeam_user"] = orjson.loads(b64decode(request.cookies.get("sunbeam-session:warriorcats")))
        else:
            return RedirectResponse("https://fateslist.xyz/frostpaw/herb?redirect=https://lynx.fateslist.xyz")

        check = await app.state.db.fetchval(
            "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", 
            int(request.scope["sunbeam_user"]["user"]["id"]), 
            request.scope["sunbeam_user"]["token"]
        )

        if not check:
            return HTMLResponse("<h1>Login and logout of Fates List to continue</h1>")

        _, perm, _ = await is_staff(None, int(request.scope["sunbeam_user"]["user"]["id"]), 2, redis=app.state.redis)

        # Only allow moderators to access the admin panel
        if perm < 3:
            return HTMLResponse("<h1>You do not have permission to access this page</h1>")

        # Perm check
        if request.url.path.startswith("/api"):
            if request.url.path == "/api/tables/" and perm < 4:
                return ORJSONResponse(["reviews", "bot_packs", "vanity", "leave_of_absence"])
            elif request.url.path == "/api/tables/users/ids/" and request.method == "GET":
                pass
            elif request.url.path in ("/api/forms/", "/api/user/", "/api/openapi.json") or request.url.path.startswith("/api/docs"):
                pass
            elif perm < 4:
                if request.url.path.startswith("/api/tables/vanity"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update vanity"}, status_code=403)
                
                elif request.url.path.startswith("/api/tables/bot_packs"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update bot packs"}, status_code=403)
                
                elif request.url.path.startswith("/api/tables/leave_of_absence/") and request.method in ("PATCH", "DELETE"):
                    ids = request.url.path.split("/")
                    loa_id = None
                    for id in ids:
                        if id.isdigit():
                            loa_id = int(id)
                            break
                    else:
                        return abort(404)
                    
                    user_id = await app.state.db.fetchval("SELECT user_id::text FROM leave_of_absence WHERE id = $1", loa_id)
                    if user_id != request.scope["sunbeam_user"]["user"]["id"]:
                        return ORJSONResponse({"error": "You do not have permission to update this leave of absence"}, status_code=403)

                elif not request.url.path.startswith(("/api/tables/reviews", "/api/tables/bot_packs", "/api/tables/leave_of_absence")):
                    return ORJSONResponse({"error": "You do not have permission to access this page"}, status_code=403)

        key = "rl:%s" % request.scope["sunbeam_user"]["user"]["id"]
        check = await app.state.redis.get(key)
        if not check:
            rl = await app.state.redis.set(key, "0", ex=30)
        if request.method != "GET":
            rl = await app.state.redis.incr(key)
            if int(rl) > 3:
                expire = await app.state.redis.ttl(key)
                await app.state.db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(128), int(request.scope["sunbeam_user"]["user"]["id"]))
                return ORJSONResponse({"error": f"You have exceeded the rate limit {expire} is TTL. API_TOKEN_RESET"}, status_code=429)

        embed = Embed(
            title = "Lynx API Request", 
            description = f"**This is usually malicious. When in doubt DM**", 
            color = 0x00ff00,
        )

        embed.add_field(name="User ID", value=request.scope["sunbeam_user"]["user"]["id"])
        embed.add_field(name="Username", value=request.scope["sunbeam_user"]["user"]["username"])
        embed.add_field(name="Request", value=f"{request.method} {request.url}")

        username = request.scope["sunbeam_user"]["user"]["username"]
        password = get_token(96)

        try:
            await BaseUser.create_user(
                username=username, 
                password=password,
                email=username + "@fateslist.xyz", 
                active=True,
                admin=True
            )

            if request.url.path == "/":
                return HTMLResponse(
                    f"""
                        <h1>Welcome to Lynx</h1>
                        <h2>Credentials for login is <code>{username}</code> and <code>{password}</code></h2>
                        <h3>You will never see this again! Take note somewhere secret, to reset this, go to /reset</h3>
                    """
                )
        except Exception as exc:
            print(exc)
        
        response = await call_next(request)

        embed.add_field(name="Status Code", value=f"{response.status_code} {HTTPStatus(response.status_code).phrase}")

        asyncio.create_task(redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"", "embed": embed.to_dict(), "channel_id": "935168801480261733"}))


        if not response.status_code < 400:
            return response

        try:
            print(request.user.user.username)
        except:
            request.scope["user"] = Unknown()

        if request.url.path.startswith("/api/tables/leave_of_absence") and request.method == "POST":
            response_body = [section async for section in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            content = response_body[0]
            content_dict = orjson.loads(content)
            await app.state.db.execute("UPDATE leave_of_absence SET user_id = $1 WHERE id = $2", int(request.scope["sunbeam_user"]["user"]["id"]), content_dict[0]["id"])
            return ORJSONResponse(content_dict)

        if request.url.path.startswith("/api/tables/bots") and request.method == "PATCH":
            print("Got bot edit, sending message")
            path = request.url.path.rstrip("/")
            bot_id = int(path.split("/")[-1])
            print("Got bot id: ", bot_id)
            owner = await app.state.db.fetchval("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id)
            embed = Embed(
                title = "Bot Edited Via Lynx", 
                description = f"Bot <@{bot_id}> has been edited via Lynx by user {request.user.user.username}", 
                color = 0x00ff00,
                url=f"https://fateslist.xyz/bot/{bot_id}"
            )
            await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})
        return response

admin = CustomHeaderMiddleware(admin)

async def server_error(request, exc):
    return HTMLResponse(content="Error", status_code=exc.status_code)

app = FastAPI(routes=[Mount("/", admin)])

@app.on_event("startup")
async def startup():
    engine = engine_finder()
    app.state.engine = engine
    app.state.redis = aioredis.from_url("redis://localhost:1001", db=1)
    app.state.db = await asyncpg.create_pool()
    await engine.start_connection_pool()

@app.on_event("shutdown")
async def close():
    await app.state.engine.close_connection_pool()
