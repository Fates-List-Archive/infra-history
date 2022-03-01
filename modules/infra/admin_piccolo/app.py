from base64 import b64decode
from os import abort
import random
import sys
import asyncpg
import asyncio

from pydantic import BaseModel
from typing import Union
import orjson
from http import HTTPStatus
import hashlib

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
from tables import Bot, Reviews, ReviewVotes, BotTag, User, Vanity, BotListTags, ServerTags, BotPack, BotCommand, LeaveOfAbsence, UserBotLogs
import orjson
import aioredis
from modules.core import redis_ipc_new
from discord import Embed
from piccolo.apps.user.tables import BaseUser
import secrets
import aiohttp
import string

def get_token(length: int) -> str:
    secure_str = ""
    for i in range(0, length):
        secure_str += secrets.choice(string.ascii_letters + string.digits)
    return secure_str

with open("config/data/discord.json") as json:
    json = orjson.loads(json.read())
    bot_logs = json["channels"]["bot_logs"]
    staff_server = json["servers"]["staff"]
    access_granted_role = json["roles"]["staff_server_access_granted_role"]

with open("config/data/secrets.json") as json:
    main_bot_token = orjson.loads(json.read())["token_main"]

async def add_role(member, role):
    url = f"https://discord.com/api/v10/guilds/{staff_server}/members/{member}/roles/{role}"
    async with aiohttp.ClientSession() as sess:
        async with sess.put(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": "[LYNX] Staff Verification"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()

admin = create_admin(
    [LeaveOfAbsence, Vanity, User, Bot, BotPack, BotCommand, BotTag, BotListTags, ServerTags, Reviews, ReviewVotes, UserBotLogs], 
    allowed_hosts = ["lynx.fateslist.xyz"], 
    production = True,
)

def code_check(code: str, user_id: int):
    expected = hashlib.sha3_384()
    expected.update(
        f"Baypaw/Flamepaw/Sunbeam/Lightleap::{user_id}".encode()
    )
    expected = expected.hexdigest()
    print(f"Expected: {expected}, but got {code}")
    if code != expected:
        return False
    return True

class Unknown:
    username = "Unknown"

# Staff Permission Checks

class StaffMember(BaseModel):
    """Represents a staff member in Fates List""" 
    name: str
    id: Union[str, int]
    perm: int
    staff_id: Union[str, int]

async def is_staff_unlocked(bot_id: int, user_id: int, redis: aioredis.Connection):
    return await redis.exists(f"fl_staff_access-{user_id}:{bot_id}")

async def is_staff(staff_json: dict | None, user_id: int, base_perm: int, json: bool = False, *, worker_session = None, redis: aioredis.Connection = None) -> Union[bool, int, StaffMember]:
    if worker_session:
        redis = worker_session.redis
    elif not redis:
        raise ValueError("No redis connection or worker_session provided")
    
    if user_id < 0: 
        staff_perm = None
    else:
        staff_perm = await redis_ipc_new(redis, "GETPERM", args=[str(user_id)], worker_session=worker_session)
    if not staff_perm:
        staff_perm = {"fname": "Unknown", "id": "0", "staff_id": "0", "perm": 0}
    else:
        staff_perm = orjson.loads(staff_perm)
    sm = StaffMember(name = staff_perm["fname"], id = staff_perm["id"], staff_id = staff_perm["staff_id"], perm = staff_perm["perm"]) # Initially
    rc = sm.perm >= base_perm
    if json:
        return rc, sm.perm, sm.dict()
    return rc, sm.perm, sm

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

        _, perm, member = await is_staff(None, int(request.scope["sunbeam_user"]["user"]["id"]), 2, redis=app.state.redis)

        # Before erroring, ensure they are perm of at least 2 and have no staff_verify_code set
        if perm >= 2:
            staff_verify_code = await app.state.db.fetchval(
                "SELECT staff_verify_code FROM users WHERE user_id = $1", 
                int(request.scope["sunbeam_user"]["user"]["id"])
            )

            if not staff_verify_code or not code_check(staff_verify_code, int(request.scope["sunbeam_user"]["user"]["id"])):
                if request.method == "POST" and request.url.path == "/_verify":
                    body = await request.json()
                    if not code_check(body["code"], int(request.scope["sunbeam_user"]["user"]["id"])):
                        return ORJSONResponse({"detail": "Invalid code"}, status_code=400)
                    else:
                        await app.state.db.execute(
                            "UPDATE users SET staff_verify_code = $1 WHERE user_id = $2", 
                            body["code"],
                            int(request.scope["sunbeam_user"]["user"]["id"]),
                        )

                        await add_role(request.scope["sunbeam_user"]["user"]["id"], access_granted_role)
                        print(f"Going to add staff role {member.staff_id}")
                        await add_role(request.scope["sunbeam_user"]["user"]["id"], member.staff_id)
                        
                        return ORJSONResponse({"detail": "Successfully verified staff member"})
                return HTMLResponse("""
                <h1>Welcome to Fates List</h1>
                <h2>Staff Verification</h2>
                <h3>In order to continue, you will need to make sure you are
                up to date with our rules</h3>
                <pre>
                <strong>You can find our staff guide <a href="https://docs.fateslist.xyz/staff-guide/info/">here</a></strong>
                
                - The code is somewhere in the staff guide so please read the full guide
                - Look up terms you do not understand on Google!
                <strong>Once you complete this, you will automatically recieve your roles in the staff server</strong>
                
                <div style="margin-left: auto; margin-right: auto; text-align: center;">
                    <textarea 
                        id="staff-verify-code"
                        placeholder="Enter staff verification code here"
                        style="background: #c8e3dd; width: 100%; height: 200px; font-size: 20px !important; resize: none; border-top: none; border-bottom: none; border-right: none"
                    ></textarea>
                </div>
                </pre>
                <br/>
                <strong>
                By continuing, you agree to:
                    <ul>
                        <li>Abide by Discord ToS</li>
                        <li>Abide by Fates List ToS</li>
                        <li>Be able to join group chats (group DMs) if required by Fates List Admin+</li>
                    </ul>
                    If you disagree with any of the above, you should stop now and consider taking a 
                    Leave Of Absence or leaving the staff team though we hope it won't come to this...
                    <br/><br/>

                    Please <em>read</em> the staff guide carefully. Do NOT just Ctrl-F. If you ask questions
                    already in the staff guide, you will just be told to reread the staff guide!
                </strong>
                <br/>
                <div id="verify-parent">
                    <button id="verify-btn" onclick="verify()">Verify</button>
                </div>
                <footer>
                    <small>&copy Copyright 2022 Fates List | <a href="https://github.com/Fates-List">Powered by Lynx</a></small>
                </footer>
                <style>
                pre, code {
                    white-space: pre-line;
                }

                html {
                    background: #c8e3dd;
                    font-size: 18px;
                    padding: 3px;
                }

                footer {
                    margin-top: 20px;
                    text-align: center;
                    font-weight: bold;
                }

                #verify-btn {
                    width: 100px;
                    background-color: red;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding: 10px;
                }

                #verify-parent {
                    text-align: center;
                }
                </style>
                <script>
                async function verify() {
                    document.querySelector("#verify-btn").innerText = "Verifying...";

                    let res = await fetch("/_verify", {
                        method: "POST",
                        credentials: 'same-origin',
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            "code": document.querySelector("#staff-verify-code").value
                        })
                    })

                    if(res.ok) {
                        document.write("<h1>Verified</h1><pre>You can now leave this page</pre>")
                    } else {
                        let json = await res.json()
                        alert("Error: " + json.detail)
                        document.querySelector("#verify-btn").innerText = "Verify";
                    }
                }
                </script>
            """)

        # Only allow mod+ to access the admin panel
        if perm < 3:
            return HTMLResponse("<h1>You do not have permission to access this page</h1>")

        # Perm check
        if request.url.path.startswith("/api"):
            if request.url.path == "/api/tables/" and perm < 4:
                return ORJSONResponse(["reviews", "review_votes", "bot_packs", "vanity", "leave_of_absence"])
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

                elif not request.url.path.startswith(("/api/tables/reviews", "/api/tables/review_votes", "/api/tables/bot_packs", "/api/tables/leave_of_absence")):
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
