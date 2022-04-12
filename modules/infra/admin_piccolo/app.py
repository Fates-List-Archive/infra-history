from base64 import b64decode
from os import abort
import pathlib
from pickletools import int4
import sys

sys.path.append("modules/infra/admin_piccolo")

import asyncpg
import asyncio

from pydantic import BaseModel
from typing import Any, Union
import orjson
from http import HTTPStatus
import hashlib
import bleach
import time
import requests
import staffapps
from dateutil import parser
import datetime
import signal

sys.path.append(".")
sys.path.append("modules/infra/admin_piccolo")
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from typing import Callable, Awaitable, Tuple, Dict, List
from starlette.responses import Response, StreamingResponse, RedirectResponse, HTMLResponse, PlainTextResponse
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
from tables import Bot, Reviews, ReviewVotes, BotTag, User, Vanity, BotListTags, ServerTags, BotPack, BotCommand, \
    LeaveOfAbsence, UserBotLogs, BotVotes, Notifications, LynxRatings, LynxSurveys, LynxSurveyResponses
import orjson
import aioredis
from modules.models import enums
from discord import Embed
from piccolo.apps.user.tables import BaseUser
import secrets
import aiohttp
import string
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.field_list import fieldlist_plugin
from mdit_py_plugins.container import container_plugin
from fastapi.staticfiles import StaticFiles
import msgpack
import enum

debug = False


class SPLDEvent(enum.Enum):
    maint = "M"
    refresh_needed = "RN"
    missing_perms = "MP"
    out_of_date = "OD"
    unsupported = "U"
    verify_needed = "VN"

async def fetch_user(user_id: int):
    async with aiohttp.ClientSession() as sess:
        async with sess.get(f"http://localhost:1234/getch/{user_id}") as resp:
            if resp.status == 404:
                return {
                    "id": "",
                    "username": "Unknown User",
                    "avatar": "https://cdn.discordapp.com/embed/avatars/0.png",
                    "disc": "0000"
                }
            return await resp.json()

async def send_message(msg: dict):
    msg["channel_id"] = int(msg["channel_id"])
    msg["embed"] = msg["embed"].to_dict()
    if not msg.get("mention_roles"):
        msg["mention_roles"] = []
    async with aiohttp.ClientSession() as sess:
        async with sess.post(f"http://localhost:1234/messages", json=msg) as res:
            return res

docs_template = requests.get("https://api.fateslist.xyz/_docs_template").text

with open("modules/infra/admin_piccolo/api-docs/endpoints.md", "w") as f:
    f.write(docs_template)

enums_docs_template = requests.get("https://api.fateslist.xyz/_enum_docs_template").text

with open("modules/infra/admin_piccolo/api-docs/enums-ref.md", "w") as f:
    f.write(enums_docs_template)


def get_token(length: int) -> str:
    secure_str = ""
    for _ in range(0, length):
        secure_str += secrets.choice(string.ascii_letters + string.digits)
    return secure_str


with open("config/data/discord.json") as json:
    json = orjson.loads(json.read())
    bot_logs = json["channels"]["bot_logs"]
    main_server = json["servers"]["main"]
    staff_server = json["servers"]["staff"]
    access_granted_role = json["roles"]["staff_server_access_granted_role"]
    bot_developer = json["roles"]["bot_dev_role"]
    certified_developer = json["roles"]["certified_dev_role"]
    certified_bot = json["roles"]["certified_bots_role"]

with open("config/data/secrets.json") as json:
    main_bot_token = orjson.loads(json.read())["token_main"]

with open("config/data/staff_roles.json") as json:
    staff_roles = orjson.loads(json.read())


async def add_role(server, member, role, reason):
    print(f"[LYNX] AddRole: {role = }, {member = }, {server = }, {reason = }")
    url = f"https://discord.com/api/v10/guilds/{server}/members/{member}/roles/{role}"
    async with aiohttp.ClientSession() as sess:
        async with sess.put(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": f"[LYNX] {reason}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()


async def del_role(server, member, role, reason):
    print(f"[LYNX] RemoveRole: {role = }, {member = }, {server = }, {reason = }")
    url = f"https://discord.com/api/v10/guilds/{server}/members/{member}/roles/{role}"
    async with aiohttp.ClientSession() as sess:
        async with sess.delete(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": f"[LYNX] {reason}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()


async def ban_user(server, member, reason):
    url = f"https://discord.com/api/v10/guilds/{server}/bans/{member}"
    async with aiohttp.ClientSession() as sess:
        async with sess.put(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": f"[LYNX] Bot Banned: {reason[:14] + '...'}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()


async def unban_user(server, member, reason):
    url = f"https://discord.com/api/v10/guilds/{server}/bans/{member}"
    async with aiohttp.ClientSession() as sess:
        async with sess.delete(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": f"[LYNX] Bot Unbanned: {reason[:14] + '...'}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()

def code_check(code: str, user_id: int):
    expected = hashlib.sha3_384()
    expected.update(
        f"Baypaw/Flamepaw/Sunbeam/Lightleap::{user_id}+Mew".encode()
    )
    expected = expected.hexdigest()
    if code != expected:
        print(f"[LYNX] CodeCheckMismatch {expected = }, {code = }")
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


async def is_staff(user_id: int, base_perm: int) -> Union[bool, int, StaffMember]:
    if user_id < 0:
        staff_perm = None
    else:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.fateslist.xyz/flamepaw/_getperm?user_id={user_id}") as res:
                staff_perm = await res.text()
                staff_perm = orjson.loads(staff_perm)
    if not staff_perm:
        staff_perm = {"fname": "Unknown", "id": "0", "staff_id": "0", "perm": 0}
    sm = StaffMember(name=staff_perm["fname"], id=staff_perm["id"], staff_id=staff_perm["staff_id"],
                     perm=staff_perm["perm"])  # Initially
    rc = sm.perm >= base_perm
    return rc, sm.perm, sm

with open("modules/infra/admin_piccolo/api-docs/staff-guide.md") as f:
    staff_guide_md = f.read()

md = (
    MarkdownIt()
        .use(front_matter_plugin)
        .use(footnote_plugin)
        .use(anchors_plugin, max_level=5, permalink=True)
        .use(fieldlist_plugin)
        .use(container_plugin, name="warning")
        .use(container_plugin, name="info")
        .use(container_plugin, name="aonly")
        .use(container_plugin, name="guidelines")
        .use(container_plugin, name="generic", validate=lambda *args: True)
        .enable('table')
        .enable('image')
)

staff_guide = md.render(staff_guide_md)

admin = create_admin(
    [Notifications, LynxSurveys, LynxSurveyResponses, LynxRatings, LeaveOfAbsence, Vanity, User, Bot, BotPack, BotCommand, BotTag, BotListTags,
     ServerTags, Reviews, ReviewVotes, UserBotLogs, BotVotes],
    allowed_hosts=["lynx.fateslist.xyz"],
    production=True,
    site_name="Lynx Admin"
)

async def auth_user_cookies(request: Request):
    if request.cookies.get("sunbeam-session:warriorcats"):
        request.scope["sunbeam_user"] = orjson.loads(b64decode(request.cookies.get("sunbeam-session:warriorcats")))
        check = await app.state.db.fetchval(
            "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2",
            int(request.scope["sunbeam_user"]["user"]["id"]),
            request.scope["sunbeam_user"]["token"]
        )
        if not check:
            print("Undoing login due to relogin requirement")
            del request.scope["sunbeam_user"]
            return

        _, _, member = await is_staff(int(request.scope["sunbeam_user"]["user"]["id"]), 2)

        request.state.member = member
    else:
        request.state.member = StaffMember(name="Unknown", id=0, perm=1, staff_id=0)

    if request.state.member.perm >= 2:
        staff_verify_code = await app.state.db.fetchval(
            "SELECT staff_verify_code FROM users WHERE user_id = $1",
            int(request.scope["sunbeam_user"]["user"]["id"])
        )

        request.state.is_verified = True

        if not staff_verify_code or not code_check(staff_verify_code, int(request.scope["sunbeam_user"]["user"]["id"])):
            request.state.is_verified = False


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/_"):
            return await call_next(request)

        print("[LYNX] Admin request. Middleware started")

        await auth_user_cookies(request)

        if not request.scope.get("sunbeam_user"):
            return RedirectResponse(f"https://fateslist.xyz/frostpaw/herb?redirect={request.url}")

        member: StaffMember = request.state.member
        perm = member.perm

        # Before erroring, ensure they are perm of at least 2 and have no staff_verify_code set
        if member.perm < 2: 
            return RedirectResponse("/missing-perms?perm=2")
        elif not request.state.is_verified:
            return RedirectResponse("/staff-verify")

        # Perm check
        if request.url.path.startswith("/admin/api"):
            if request.url.path == "/admin/api/tables/" and perm < 4:
                return ORJSONResponse(
                    ["reviews", "review_votes", "bot_packs", "vanity", "leave_of_absence", "user_vote_table",
                     "lynx_rating"])
            elif request.url.path == "/admin/api/tables/users/ids/" and request.method == "GET":
                pass
            elif request.url.path in (
                    "/admin/api/forms/", "/admin/api/user/", "/admin/api/openapi.json") or request.url.path.startswith(
                "/admin/api/docs"):
                pass
            elif perm < 4:
                if request.url.path.startswith("/admin/api/tables/vanity"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update vanity"}, status_code=403)

                elif request.url.path.startswith("/admin/api/tables/bot_packs"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update bot packs"},
                                              status_code=403)

                elif request.url.path.startswith("/admin/api/tables/leave_of_absence/") and request.method in (
                        "PATCH", "DELETE"):
                    ids = request.url.path.split("/")
                    loa_id = None
                    for id in ids:
                        if id.isdigit():
                            loa_id = int(id)
                            break
                    else:
                        return abort(404)

                    user_id = await app.state.db.fetchval("SELECT user_id::text FROM leave_of_absence WHERE id = $1",
                                                          loa_id)
                    if user_id != request.scope["sunbeam_user"]["user"]["id"]:
                        return ORJSONResponse({"error": "You do not have permission to update this leave of absence"},
                                              status_code=403)

                elif not request.url.path.startswith(("/admin/api/tables/reviews", "/admin/api/tables/review_votes",
                                                      "/admin/api/tables/bot_packs",
                                                      "/admin/api/tables/user_vote_table",
                                                      "/admin/api/tables/leave_of_absence",
                                                      "/admin/api/tables/lynx_rating")):
                    return ORJSONResponse({"error": "You do not have permission to access this page"}, status_code=403)

        key = "rl:%s" % request.scope["sunbeam_user"]["user"]["id"]
        check = await app.state.redis.get(key)
        if not check:
            rl = await app.state.redis.set(key, "0", ex=30)
        if request.method != "GET":
            rl = await app.state.redis.incr(key)
            if int(rl) > 10:
                expire = await app.state.redis.ttl(key)
                await app.state.db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(128),
                                           int(request.scope["sunbeam_user"]["user"]["id"]))
                return ORJSONResponse({"detail": f"[LYNX] RatelimitError: {expire=}; API_TOKEN_RESET"},
                                      status_code=429)

        embed = Embed(
            title="Lynx API Request",
            description=f"**This is usually malicious. When in doubt DM**",
            color=0x00ff00,
        )

        embed.add_field(name="User ID", value=request.scope["sunbeam_user"]["user"]["id"])
        embed.add_field(name="Username", value=request.scope["sunbeam_user"]["user"]["username"])
        embed.add_field(name="Request", value=f"{request.method} {request.url}")

        if request.url.path.startswith("/meta"):
            return ORJSONResponse({"piccolo_admin_version": "0.1a1", "site_name": "Lynx Admin"})

        request.state.user_id = int(request.scope["sunbeam_user"]["user"]["id"])

        response = await call_next(request)

        embed.add_field(name="Status Code", value=f"{response.status_code} {HTTPStatus(response.status_code).phrase}")

        await app.state.db.execute(
            "INSERT INTO lynx_logs (user_id, method, url, status_code) VALUES ($1, $2, $3, $4)",
            int(request.scope["sunbeam_user"]["user"]["id"]),
            request.method,
            str(request.url),
            response.status_code
        )

        if not response.status_code < 400:
            return response

        try:
            print(request.user.user.username)
        except:
            request.scope["user"] = Unknown()

        if request.url.path.startswith("/admin/api/tables/leave_of_absence") and request.method == "POST":
            response_body = [section async for section in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            content = response_body[0]
            content_dict = orjson.loads(content)
            await app.state.db.execute("UPDATE leave_of_absence SET user_id = $1 WHERE id = $2",
                                       int(request.scope["sunbeam_user"]["user"]["id"]), content_dict[0]["id"])
            return ORJSONResponse(content_dict)

        if request.url.path.startswith("/admin/api/tables/bots") and request.method == "PATCH":
            print("Got bot edit, sending message")
            path = request.url.path.rstrip("/")
            bot_id = int(path.split("/")[-1])
            print("Got bot id: ", bot_id)
            owner = await app.state.db.fetchval("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id)
            embed = Embed(
                title="Bot Edited Via Lynx",
                description=f"Bot <@{bot_id}> has been edited via Lynx by user {request.user.user.username}",
                color=0x00ff00,
                url=f"https://fateslist.xyz/bot/{bot_id}"
            )
            await send_message({"content": f"<@{owner}>", "embed": embed, "channel_id": bot_logs})

        return response


admin = CustomHeaderMiddleware(admin)


async def server_error(request, exc):
    return HTMLResponse(content="Error", status_code=exc.status_code)


app = FastAPI(routes=[
    Mount("/admin", admin),
    Mount("/_static", StaticFiles(directory="modules/infra/admin_piccolo/static")),
],
    docs_url="/_docs",
    openapi_url="/_openapi"
)

def bot_select(id: str, bot_list: list[str], reason: bool = False):
    select = f"""
<label for='{id}'>Choose a bot</label><br/>
<select name='{id}' {id=}> 
<option value="" disabled selected>Select your option</option>
    """

    for bot in bot_list:
        select += f"""
<option value="{bot['bot_id']}">{bot['username_cached'] or 'No cached username'} ({bot['bot_id']})</option>
        """

    select += "</select><br/>"

    # Add a input for bot id instead of select
    select += f"""
<label for="{id}-alt">Or enter a Bot ID</label><br/>
<input type="number" id="{id}-alt" name="{id}-alt"/>
<br/>
    """

    if reason:
        select += f"""
<label for="{id}-reason">Reason</label><br/>
<textarea 
    type="text" 
    id="{id}-reason" 
    name="{id}-reason"
    placeholder="Enter reason and feedback for improvement here"
></textarea>
<br/>
        """

    return select

class ActionWithReason(BaseModel):
    bot_id: str
    owners: list[dict] | None = None  # This is filled in by action decorator
    main_owner: int | None = None  # This is filled in by action decorator
    context: Any | None = None
    reason: str


app.state.bot_actions = {}


def action(
        name: str,
        states: list[enums.BotState],
        min_perm: int = 2,
        action_log: enums.UserBotAction | None = None
):
    async def state_check(bot_id: int):
        bot_state = await app.state.db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        return (bot_state in states) or len(states) == 0

    async def _core(ws: WebSocket, data: ActionWithReason):
        if ws.state.member.perm < min_perm:
            return {
                "resp": "bot_action",
                "detail": f"PermError: {min_perm=}, {ws.state.member.perm=}"
            }

        if not data.bot_id.isdigit():
            return {
                "resp": "bot_action",
                "detail": "Bot ID is invalid"
            }

        data.bot_id = int(data.bot_id)

        if not await state_check(data.bot_id):
            return {
                "resp": "bot_action",
                "detail": replace_if_web(f"Bot state check error: {states=}", ws)
            }

        data.owners = await app.state.db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", data.bot_id)

        for owner in data.owners:
            if owner["main"]:
                data.main_owner = owner["owner"]
                break
    
    def decorator(function):
        async def wrapper(ws: WebSocket, data: ActionWithReason):
            if _data := await _core(ws, data):
                return _data # Already sent ws message, ignore
            if len(data.reason) < 5:
                return {
                    "resp": "bot_action",
                    "detail": "Reason must be more than 5 characters"
                }

            ws.state.user_id = int(ws.state.user["id"])

            res = await function(ws, data)  # Fake Websocket as Request for now TODO: Make this not fake
            
            err = res.get("err", False)
            
            if action_log and not err:
                await app.state.db.execute("INSERT INTO user_bot_logs (user_id, bot_id, action, context) VALUES ($1, $2, $3, $4)", ws.state.user_id, data.bot_id, action_log.value, data.reason)

            res = jsonable_encoder(res)
            res["resp"] = "bot_action"

            if not err:
                # Tell client that a refresh is needed as a bot action has taken place
                await manager.broadcast({"resp": "spld", "e": SPLDEvent.refresh_needed, "loc": "/bot-actions"})
            return res

        app.state.bot_actions[name] = wrapper
        return wrapper

    return decorator


@action("claim", [enums.BotState.pending], action_log=enums.UserBotAction.claim)
async def claim(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3",
                               enums.BotState.under_review, request.state.user_id, int(data.bot_id))

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Claimed",
        description=f"<@{request.state.user_id}> has claimed <@{data.bot_id}> and this bot is now under review.\n**If all goes well, this bot should be approved (or denied) soon!**\n\nThank you for using Fates List :heart:",
    )

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})
    return {"detail": "Successfully claimed bot!"}


@action("unclaim", [enums.BotState.under_review], action_log=enums.UserBotAction.unclaim)
async def unclaim(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Unclaimed",
        description=f"<@{request.state.user_id}> has stopped testing <@{data.bot_id}> for now and this bot is now pending review from another bot reviewer.\n**This is perfectly normal. All bot reviewers need breaks too! If all goes well, this bot should be approved (or denied) soon!**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})
    return {"detail": "Successfully unclaimed bot"}


@action("approve", [enums.BotState.under_review], action_log=enums.UserBotAction.approve)
async def approve(request: Request, data: ActionWithReason):
    # Get approximate guild count
    async with aiohttp.ClientSession() as sess:
        async with sess.get(f"https://japi.rest/discord/v1/application/{data.bot_id}") as resp:
            if resp.status != 200:
                return ORJSONResponse({
                    "detail": f"Bot does not exist or japi.rest is down. Got status code {resp.status}"
                }, status_code=400)
            japi = await resp.json()
            approx_guild_count = japi["data"]["bot"]["approximate_guild_count"]

    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2, guild_count = $3 WHERE bot_id = $4",
                               enums.BotState.approved, request.state.user_id, approx_guild_count, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Approved!",
        description=f"<@{request.state.user_id}> has approved <@{data.bot_id}>\nCongratulations on your accompishment and thank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)
    embed.add_field(name="Guild Count (approx)", value=str(approx_guild_count))

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    for owner in data.owners:
        asyncio.create_task(add_role(main_server, owner["owner"], bot_developer, "Bot Approved"))

    return {"detail": "Successfully approved bot", "guild_id": str(main_server), "bot_id": str(data.bot_id)}


@action("deny", [enums.BotState.under_review], action_log=enums.UserBotAction.deny)
async def deny(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.denied,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Denied",
        description=f"<@{request.state.user_id}> has denied <@{data.bot_id}>!\n**Once you've fixed what we've asked you to fix, please resubmit your bot by going to `Bot Settings`.**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully denied bot"}


@action("ban", [enums.BotState.approved], min_perm=4, action_log=enums.UserBotAction.ban)
async def ban(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.banned,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Banned",
        description=f"<@{request.state.user_id}> has banned <@{data.bot_id}>!\n**Once you've fixed what we've need you to fix, please appeal your ban by going to `Bot Settings`.**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    asyncio.create_task(ban_user(main_server, data.bot_id, data.reason))

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully banned bot"}


@action("unban", [enums.BotState.banned], min_perm=4, action_log=enums.UserBotAction.unban)
async def unban(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.approved,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Unbanned",
        description=f"<@{request.state.user_id}> has unbanned <@{data.bot_id}>!\n\nThank you for using Fates List again and sorry for any inconveniences caused! :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    asyncio.create_task(unban_user(main_server, data.bot_id, data.reason))

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully unbanned bot"}


@action("certify", [enums.BotState.approved], min_perm=5, action_log=enums.UserBotAction.certify)
async def certify(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.certified,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Certified",
        description=f"<@{request.state.user_id}> has certified <@{data.bot_id}>.\n**Good Job!!!**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Feedback", value=data.reason)

    for owner in data.owners:
        asyncio.create_task(
            add_role(main_server, owner["owner"], certified_developer, "Bot certified - owner gets role"))

    # Add certified bot role to bot
    asyncio.create_task(add_role(main_server, data.bot_id, certified_bot, "Bot certified - add bots role"))

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully certified bot"}


@action("uncertify", [enums.BotState.certified], min_perm=5, action_log=enums.UserBotAction.uncertify)
async def uncertify(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.approved, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Uncertified",
        description=f"<@{request.state.user_id}> has uncertified <@{data.bot_id}>.\n\nThank you for using Fates List but this was a necessary action :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    for owner in data.owners:
        asyncio.create_task(
            del_role(main_server, owner["owner"], certified_developer, "Bot uncertified - Owner gets role"))

    # Add certified bot role to bot
    asyncio.create_task(del_role(main_server, data.bot_id, certified_bot, "Bot uncertified - Bots Role"))

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully uncertified bot"}


@action("unverify", [enums.BotState.approved], min_perm=3, action_log=enums.UserBotAction.unverify)
async def unverify(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.pending,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Unverified",
        description=f"<@{request.state.user_id}> has unverified <@{data.bot_id}> due to some issues we are looking into!\n\nThank you for using Fates List and we thank you for your patience :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully unverified bot"}


@action("requeue", [enums.BotState.banned, enums.BotState.denied], min_perm=3, action_log=enums.UserBotAction.requeue)
async def requeue(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.pending,
                               request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0x00ff00,
        title="Bot Requeued",
        description=f"<@{request.state.user_id}> has requeued <@{data.bot_id}> for re-review!\n\nThank you for using Fates List and we thank you for your patience :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully requeued bot"}


@action("reset-votes", [], min_perm=3)
async def reset_votes(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET votes = 0 WHERE bot_id = $1", data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Votes Reset",
        description=f"<@{request.state.user_id}> has force resetted <@{data.bot_id}> votes due to abuse!\n\nThank you for using Fates List and we are sorry for any inconveniences caused :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully reset bot votes"}


@action("reset-all-votes", [], min_perm=5)
async def reset_all_votes(request: Request, data: ActionWithReason):
    if data.reason == "STUB_REASON":
        data.reason = "Monthly Vote Reset"

    async with app.state.db.acquire() as conn:
        top_voted = await conn.fetch("SELECT bot_id, username_cached, votes, total_votes FROM bots WHERE state = 0 OR "
                                     "state = 6 ORDER BY votes DESC, total_votes DESC LIMIT 7")
        async with conn.transaction():
            bots = await app.state.db.fetch("SELECT bot_id, votes FROM bots")
            for bot in bots:
                await conn.execute("INSERT INTO bot_stats_votes_pm (bot_id, epoch, votes) VALUES ($1, $2, $3)",
                                   bot["bot_id"], time.time(), bot["votes"])
            await conn.execute("UPDATE bots SET votes = 0")
            await conn.execute("DELETE FROM user_vote_table")

    embed = Embed(
        url="https://fateslist.xyz",
        title="All Bot Votes Reset",
        color=0x00ff00,
        description=f"<@{request.state.user_id}> has resetted all votes!\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    top_voted_str = ""
    i = 1
    for bot in top_voted:
        add = f"**#{i}.** [{bot['username_cached'] or 'Uncached User'}](https://fateslist.xyz/bot/{bot['bot_id']}) - {bot['votes']} votes this month and {bot['total_votes']} total votes. GG!\n"
        if len(top_voted_str) + len(add) > 2048:
            break
        else:
            top_voted_str += add
        i += 1

    embed.add_field(name="Top Voted", value=top_voted_str)

    await send_message({"content": "", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully reset all bot votes"}


@action("set-flag", [], min_perm=3)
async def set_flag(request: Request, data: ActionWithReason):
    if not isinstance(data.context, int):
        return {"detail": "Flag must be an integer", "err": True}
    try:
        flag = enums.BotFlag(data.context)
    except:
        return {"detail": "Flag must be of enum Flag", "err": True}

    existing_flags = await app.state.db.fetchval("SELECT flags FROM bots WHERE bot_id = $1", data.bot_id)
    existing_flags = existing_flags or []
    existing_flags = set(existing_flags)
    existing_flags.add(int(flag))

    try:
        existing_flags.remove(int(enums.BotFlag.unlocked))
    except:
        pass

    existing_flags = list(existing_flags)
    existing_flags.sort()
    await app.state.db.fetchval("UPDATE bots SET flags = $1 WHERE bot_id = $2", existing_flags, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Flag Updated",
        description=f"<@{request.state.user_id}> has modified the flags of <@{data.bot_id}> with addition of {flag.name} ({flag.value}) -> {flag.__doc__} !\n\nThank you for using Fates List and we are sorry for any inconveniences caused :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully set flag"}


@action("unset-flag", [], min_perm=3)
async def unset_flag(request: Request, data: ActionWithReason):
    if not isinstance(data.context, int):
        return {"detail": "Flag must be an integer", "err": True}
    try:
        flag = enums.BotFlag(data.context)
    except:
        return {"detail": "Flag must be of enum Flag", "err": True}

    existing_flags = await app.state.db.fetchval("SELECT flags FROM bots WHERE bot_id = $1", data.bot_id)
    existing_flags = existing_flags or []
    existing_flags = set(existing_flags)
    try:
        existing_flags.remove(int(flag))
    except:
        return {"detail": "Flag not on this bot", "err": True}

    try:
        existing_flags.remove(int(enums.BotFlag.unlocked))
    except:
        pass

    existing_flags = list(existing_flags)
    existing_flags.sort()
    await app.state.db.fetchval("UPDATE bots SET flags = $1 WHERE bot_id = $2", existing_flags, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}",
        color=0xe74c3c,
        title="Bot Flag Updated",
        description=f"<@{request.state.user_id}> has modified the flags of <@{data.bot_id}> with removal of {flag.name} ({flag.value}) -> {flag.__doc__} !\n\nThank you for using Fates List and we are sorry for any inconveniences caused :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.main_owner}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully unset flag"}

# Lynx base websocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict | list, websocket: WebSocket):
        ## REMOVE WHEN SQUIRREL SUPPORTS SPLD LIKE WEB DOES
        if websocket.state.plat == "SQUIRREL" and message.get("resp") == "spld":
            # Not supported by squirrel yet
            message = {"resp": "index", "detail": f"{message.get('e', 'Unknown SPLD event')}"}
        
        try:
            if websocket.state.debug:
                print(f"Sending message: {websocket.client.host=}, {message=}")
                await websocket.send_json(jsonable_encoder(message))
            else:
                await websocket.send_bytes(msgpack.packb(jsonable_encoder(message)))
        except RuntimeError as e:
            try:
                await websocket.close(1008)
            except:
                ...

    async def broadcast(self, message: dict | list):
        for connection in self.active_connections:
            await manager.send_personal_message(message, connection)
    
manager = ConnectionManager()

ws_action_dict = {
}

def ws_action(name: str):
    def decorator(func: Callable):
        ws_action_dict[name] = func
        return func
    return decorator

@ws_action("apply_staff")
async def apply_staff(ws: WebSocket, data: dict):
    if ws.state.member.perm == -1:
        return {"resp": "apply_staff", "detail": "You must be logged in to create staff applications!"}

    for pane in staffapps.questions:
        for question in pane.questions:
            answer = data["answers"].get(question.id)
            if not answer:
                return {"resp": "apply_staff", "detail": f"Missing answer for question {question.id}"}
            elif len(answer) < question.min_length:
                return {"resp": "apply_staff", "detail": f"Answer for question {question.id} is too short"}
            elif len(answer) > question.max_length:
                return {"resp": "apply_staff", "detail": f"Answer for question {question.id} is too long"}
    
    await app.state.db.execute(
        "INSERT INTO lynx_apps (user_id, questions, answers, app_version) VALUES ($1, $2, $3, $4)",
        int(ws.state.user["id"]),
        orjson.dumps(jsonable_encoder(staffapps.questions)).decode(),
        orjson.dumps(data["answers"]).decode(),
        3
    )

    return {"resp": "apply_staff", "detail": "Successfully applied for staff!"}

@ws_action("get_sa_questions")
async def get_sa_questions(ws: WebSocket, _):
    """Get staff app questions"""
    questions = '<form class="needs-validation" novalidate><div class="form-group">'

    for pane in staffapps.questions:
        questions += f"""

### {pane.title}

{pane.description}
        """
        for question in pane.questions:
            questions += f"""
#### {question.title}

<div class="form-group">

<label for="{question.id}">{question.question} ({question.min_length} - {question.max_length} characters)</label>

{question.description}. 

"""
            if question.paragraph:
                questions += f"""
<textarea class="form-control question" id="{question.id}" name="{question.id}" placeholder="{question.description}" minlength="{question.min_length}" maxlength="{question.max_length}" required aria-required="true"></textarea>
"""
            else:
                questions += f"""
<input type="{question.type}" class="form-control question" id="{question.id}" name="{question.id}" placeholder="{question.description}" minlength="{question.min_length}" maxlength="{question.max_length}" required aria-required="true"/>
"""
            questions += f"""
<div class="valid-feedback">
    Looks good!
</div>
<div class="invalid-feedback">
    {question.title} is either missing, too long or too short!
</div>

**Write a minimum of {question.min_length} characters and a maximum of {question.max_length} characters.**

<br/>
</div>
            """

        questions += "</div>"

    questions += """
</div>
<button type="submit" id="apply-btn">Apply</button>
</form>
    """

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {
        "resp": "get_sa_questions",
        "title": "Apply For Staff",
        "data": md.render(f"""
We're always open, don't worry!

{questions}
        """),
        "ext_script": "apply",
    }


@ws_action("loa")
async def loa(ws: WebSocket, _):
    if ws.state.member.perm < 2:
        return {"resp": "spld", "e": SPLDEvent.missing_perms}
    elif not ws.state.verified:
        return {"resp": "spld", "e": SPLDEvent.verify_needed}

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {
        "resp": "loa",
        "title": "Leave Of Absense",
        "pre": "/links",
        "data": md.render(f"""
::: warning

Please don't abuse this by spamming LOA's non-stop or you **will** be demoted!

:::

There are *two* ways of creating a LOA.

### Simple Form

<form class="needs-validation" novalidate>
    <div class="form-group">
        <label for="reason">Reason</label>
        <textarea class="form-control question" id="reason" name="reason" placeholder="Reason for LOA" required aria-required="true"></textarea>
        <div class="valid-feedback">
            Looks good!
        </div>
        <div class="invalid-feedback">
            Reason is either missing or too long!
        </div>
    </div>
    <div class="form-group">
        <label for="duration">Duration</label>
        <input type="datetime-local" class="form-control question" id="duration" name="duration" placeholder="Duration of LOA" required aria-required="true"/>
        <div class="valid-feedback">
            Looks good!
        </div>
        <div class="invalid-feedback">
            Duration is either missing or too long!
        </div>
    </div>
    <button type="submit" id="loa-btn">Submit</button>
</form>

### Piccolo Admin

<ol>
    <li>Login to Lynx Admin</li>
    <li>Click Leave Of Absense</li>
    <li>Click 'Add Row'</li>
    <li>Fill out the nessesary fields</li>
    <li>Click 'Save'</li>
</ol>
    """),
    "ext_script": "apply",    
    }

@ws_action("send_loa")
async def send_loa(ws: WebSocket, data: dict):
    if ws.state.member.perm < 2:
        return {"resp": "spld", "e": SPLDEvent.missing_perms}
    if not data.get("answers"):
        return {"resp": "send_loa", "detail": "You did not fill out the form correctly"}
    if not data["answers"]["reason"]:
        return {"resp": "send_loa", "detail": "You did not fill out the form correctly"}
    if not data["answers"]["duration"]:
        return {"resp": "send_loa", "detail": "You did not fill out the form correctly"}
    try:
        date = parser.parse(data["answers"]["duration"])
    except:
        return {"resp": "send_loa", "detail": "You did not fill out the form correctly"}
    if date.year - datetime.datetime.now().year not in (0, 1):
        return {"resp": "send_loa", "detail": "Duration must be in within this year"}

    await app.state.db.execute(
        "INSERT INTO leave_of_absence (user_id, reason, estimated_time, start_date) VALUES ($1, $2, $3, $4)",
        int(ws.state.user["id"]),
        data["answers"]["reason"],
        date - datetime.datetime.now(),
        datetime.datetime.now(),
    )

    return {"resp": "send_loa", "detail": "Submitted LOA successfully"}

@ws_action("staff_apps")
async def staff_apps(ws: WebSocket, data: dict):
    # Get staff application list
    if ws.state.member.perm < 2:
        return {"resp": "spld", "e": SPLDEvent.missing_perms}
    elif not ws.state.verified:
        return {"resp": "spld", "e": SPLDEvent.verify_needed}

    staff_apps = await app.state.db.fetch(
        "SELECT user_id, app_id, questions, answers, created_at FROM lynx_apps ORDER BY created_at DESC")
    app_html = ""

    for staff_app in staff_apps:
        if str(staff_app["app_id"]) == data.get("open", ""):
            open_attr = "open"
        else:
            open_attr = ""
        user = await fetch_user(staff_app['user_id'])
        user["username"] = bleach.clean(user["username"])

        questions = orjson.loads(staff_app["questions"])
        answers = orjson.loads(staff_app["answers"])

        questions_html = ""

        for pane in questions:
            questions_html += f"<h3>{pane['title']}</h3><strong>Prelude</strong>: {pane['description']}<br/>"
            for question in pane["questions"]:
                questions_html += f"""
                    <h4>{question['title']}</h4>
                    <pre class="pre">
                        <strong>ID:</strong> {question['id']}
                        <strong>Minimum Length:</strong> {question['min_length']}
                        <strong>Maximum Length:</strong> {question['max_length']}
                        <strong>Question:</strong> {question['question']}
                        <strong>Answer:</strong> {bleach.clean(answers[question['id']])}
                    </pre>
                """

        app_html += f"""
        <details {open_attr}>
            <summary>{staff_app['app_id']}</summary>
            <h2>User Info</h2>
            <p><strong><em>Created At:</em></strong> {staff_app['created_at']}</p>
            <p><strong><em>User:</em></strong> {bleach.clean(user['username'])} ({user['id']})</p>
            <h2>Application:</h2> 
            {questions_html}
            <br/>
            <button onclick="window.location.href = '/addstaff?add_staff_id={user['id']}'">Accept</button>
            <button onclick="deleteAppByUser('{user['id']}')">Delete</button>
        </details>
        """

    return {
        "resp": "staff_apps",
        "title": "Staff Application List",
        "pre": "/links",
        "data": f"""
        <p>Please verify applications fairly</p>
        {app_html}
        <br/>
        """,
        "ext_script": "user-actions",
    }

@ws_action("user_actions")
async def user_actions(ws: WebSocket, data: dict):
    data = data.get("data", {})
    # Easiest way to block cross origin is to just use a hidden input
    if ws.state.member.perm < 3:
        return {"resp": "spld", "e": SPLDEvent.missing_perms, "min_perm": 3}
    elif not ws.state.verified:
        return {"resp": "spld", "e": SPLDEvent.verify_needed}

    user_state_select = """
<label for='user_state_select'>New State</label><br/>
<select name='user_state_select' id='user_state_select'> 
    """

    for state in list(enums.UserState):
        user_state_select += f"""
<option value={state.value}>{state.name} ({state.value}) -> {state.__doc__}</option>
        """
    user_state_select += "</select>"

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {
        "resp": "user_actions",
        "title": "User Actions",
        "data": md.render(f"""
## For refreshers, the staff guide is here:

{staff_guide_md}

<hr/>

Now that we're all caught up with the staff guide, here are the list of actions you can take:

::: action-addstaff

### Add Staff

- Head Admin+ only
- Definition: user => bot_reviewer

<label for="staff_user_id">User ID</label>
<input class="form-control" id="staff_user_id" name="staff_user_id" placeholder='user id here' type="number" value="{data.get("add_staff_id") or ''}" />
<button onclick="addStaff()">Add</button>

:::

::: action-userstate

### Set User State

- Admin+ only
- Definition: state => $user_state

<label for="user_state_id">User ID</label>
<input class="form-control" id="user_state_id" name="user_state_id" placeholder='user id here' type="number" />

{user_state_select}

<label for="user_state_reason">Reason</label>
<textarea 
type="text" 
id="user_state_reason" 
name="user_state_reason"
placeholder="Enter reason for state change here!"
></textarea>

<button onclick="setUserState()">Set State</button>

:::
        """),
        "ext_script": "user-actions",
    }

@ws_action("bot_actions")
async def bot_actions(ws: WebSocket, _):
    if ws.state.member.perm < 2:
        return {"resp": "spld", "e": SPLDEvent.missing_perms}
    elif not ws.state.verified:
        return {"resp": "spld", "e": SPLDEvent.verify_needed}

    queue = await app.state.db.fetch(
        "SELECT bot_id, username_cached, description, prefix, created_at FROM bots WHERE state = $1 ORDER BY created_at ASC",
        enums.BotState.pending)

    queue_select = bot_select("queue", queue)

    under_review = await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1",
                                            enums.BotState.under_review)

    under_review_select_approved = bot_select("under_review_approved", under_review, reason=True)
    under_review_select_denied = bot_select("under_review_denied", under_review, reason=True)
    under_review_select_claim = bot_select("under_review_claim", under_review, reason=True)

    approved = await app.state.db.fetch(
        "SELECT bot_id, username_cached FROM bots WHERE state = $1 ORDER BY created_at DESC",
        enums.BotState.approved)

    ban_select = bot_select("ban", approved, reason=True)
    certify_select = bot_select("certify", approved, reason=True)
    unban_select = bot_select("unban",
                                await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1",
                                                        enums.BotState.banned), reason=True)
    unverify_select = bot_select("unverify", await app.state.db.fetch(
        "SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.approved), reason=True)
    requeue_select = bot_select("requeue", await app.state.db.fetch(
        "SELECT bot_id, username_cached FROM bots WHERE state = $1 OR state = $2", enums.BotState.denied,
        enums.BotState.banned), reason=True)

    uncertify_select = bot_select("uncertify", await app.state.db.fetch(
        "SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.certified), reason=True)

    reset_bot_votes_select = bot_select("reset-votes", await app.state.db.fetch(
        "SELECT bot_id, username_cached FROM bots WHERE state = $1 OR state = $2", enums.BotState.approved,
        enums.BotState.certified), reason=True)

    flag_list = list(enums.BotFlag)
    flags_select = "<label>Select Flag</label><select id='flag' name='flag'>"
    for flag in flag_list:
        flags_select += f"<option value={flag.value}>{flag.name} ({flag.value}) -> {flag.__doc__}</option>"
    flags_select += "</select>"

    flags_bot_select = bot_select("set-flag", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots"),
                                    reason=True)

    queue_md = ""

    for bot in queue:
        owners = await app.state.db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot["bot_id"])

        owners_md = ""

        for owner in owners:
            user = await fetch_user(owner["owner"])
            owners_md += f"""\n     - {user['username']}  ({owner['owner']}) |  main -> {owner["main"]}"""

        queue_md += f"""
{bot['username_cached']} | [Site Page](https://fateslist.xyz/bot/{bot['bot_id']})

- Prefix: {bot['prefix'] or '/'}
- Description: {bleach.clean(bot['description'])}
- Owners: {owners_md}
- Created At: {bot['created_at']}

"""

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {
        "resp": "bot_actions",
        "title": "Bot Actions",
        "pre": "/links",
        "data": md.render(f"""
## For refreshers, the staff guide is here:

{staff_guide_md}

<hr/>

Now that we're all caught up with the staff guide, here are the list of actions you can take:

## Bot Queue

::: info 

Please check site pages before approving/denying. You can save lots of time by doing this!

:::

{queue_md}

## Actions

::: action-claim

### Claim Bot

- Only claim bots you have the *time* to review
- Please unclaim bots whenever you are no longer actively reviewing them
- Definition: pending => under_review

{queue_select}
<button onclick="claim()">Claim</button>

:::

::: action-unclaim

### Unclaim Bot

- Please unclaim bots whenever you are no longer actively reviewing them
- Definition: under_review => pending

{under_review_select_claim}
<button onclick="unclaim()">Unclaim</button>

:::

::: action-approve

### Approve Bot 

<span id='approve-invite'></span>

- You must claim this bot before approving and preferrably before testing
- Definition: under_review => approved

{under_review_select_approved}

<button onclick="approve()">Approve</button>

:::

::: action-deny

### Deny Bot

- You must claim this bot before denying and preferrably before testing
- Definition: under_review => deny

{under_review_select_denied}
<button onclick="deny()">Deny</button>

:::

::: action-ban

### Ban Bot 

- Admin+ only
- Must be approved and *not* certified
- Definition: approved => banned

{ban_select}
<button onclick="ban()">Ban</button>

:::

::: action-unban

### Unban Bot

- Admin+ only
- Must *already* be banned
- Definition: banned => approved

{unban_select}
<button onclick="unban()">Unban</button>

:::

::: action-certify

### Certify Bot

- Head Admin+ only
- Definition: approved => certified

{certify_select}
<button onclick="certify()">Certify</button>

:::

::: action-uncertify

### Uncertify Bot

- Head Admin+ only
- Definition: certified => approved

{uncertify_select}
<button onclick="uncertify()">Uncertify</button>

:::

::: action-unverify

### Unverify Bot

- Moderator+ only
- Definition: approved => under_review

{unverify_select}
<button onclick="unverify()">Unverify</button>

:::

::: action-requeue

### Requeue Bot

- Moderator+ only
- Definition: denied | banned => under_review

{requeue_select}
<button onclick="requeue()">Requeue</button>

:::

::: action-reset-votes

### Reset Bot Votes

- Moderator+ only
- Definition: votes => 0

{reset_bot_votes_select}
<button onclick="resetVotes()">Reset</button>

:::

::: action-reset-all-votes

### Reset All Votes

- Head Admin+ only
- Definition: votes => 0 %all%

<textarea
id="reset-all-votes-reason"
placeholder="Reason for resetting all votes. Defaults to 'Monthly Votes Reset'"
></textarea>

<button onclick="resetAllVotes()">Reset All</button>

:::

::: action-setflag

### Set/Unset Bot Flag

- Moderator+ only
- Definition: flag => flags.intersection(flag)

{flags_bot_select}

{flags_select}

<div class="form-check">
<input class="form-check-input" type="checkbox" id="unset" name="unset" />
<label class="form-check-label" for="unset">Unset Flag (unchecked = Set)</label>
</div>

<button onclick="setFlag()">Update</button>
:::
"""),
        "ext_script": "bot-actions",
    }

@ws_action("staff_verify")
async def staff_verify(ws: WebSocket, _):
    if ws.state.member.perm < 2:
        return {"resp": "spld", "e": SPLDEvent.missing_perms}
    return {
        "resp": "staff_verify",
        "title": "Fates List Staff Verification",
        "data": """
<h3>In order to continue, you will need to make sure you are up to date with our rules</h3>
<pre>
<strong>You can find our staff guide <a href="https://lynx.fateslist.xyz/staff-guide">here</a></strong>

- The code is somewhere in the staff guide so please read the full guide
- Look up terms you do not understand on Google!
<strong>Once you complete this, you will automatically recieve your roles in the staff server</strong>
</pre>

<div style="margin-left: auto; margin-right: auto; text-align: center;">
<div class="form-group">
<textarea class="form-control" id="staff-verify-code"
placeholder="Enter staff verification code here"
></textarea>
</div>
</div>
<strong>
By continuing, you agree to:
<ul>
<li>Abide by Discord ToS</li>
<li>Abide by Fates List ToS</li>
<li>Agree to try and be at least partially active on the list</li>
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
</div>""",
        "script": """
async function verify() {
    document.querySelector("#verify-btn").innerText = "Verifying...";
    let code = document.querySelector("#staff-verify-code").value

    wsSend({request: "cosmog", code: code})
}
"""
    }

@ws_action("notifs")
async def notifs(ws: WebSocket, _):
    notifs = await app.state.db.fetch("SELECT id, acked_users, message, type, staff_only FROM lynx_notifications")
    _send_notifs = []
    for notif in notifs:
        if notif["staff_only"]:
            if ws.state.member.perm >= 2:
                _send_notifs.append(notif)
        elif notif["acked_users"]:
            if ws.state.user and int(ws.state.user["id"]) in notif["acked_users"]:
                _send_notifs.append(notif)
        else:
            _send_notifs.append(notif)
    return {"resp": "notifs", "data": _send_notifs}

@ws_action("doctree")
async def doctree(ws: WebSocket, _):
    docs = []

    for path in pathlib.Path("modules/infra/admin_piccolo/api-docs").rglob("*.md"):
        proper_path = str(path).replace("modules/infra/admin_piccolo/api-docs/", "")
        
        docs.append(proper_path.split("/"))
    
    return {"resp": "doctree", "tree": docs}

@ws_action("docs")
async def docs(ws: WebSocket, data: dict):
    page = data.get("path", "/").split("#")[0]
    source = data.get("source", False)

    if page.endswith(".md"):
        page = f"/docs/{page[:-3]}"

    elif not page or page == "/docs":
        page = "/index"

    if not page.replace("-", "").replace("_", "").replace("/", "").replace("!", "").isalnum():
        return {"resp": "docs", "detail": "Invalid page"}

    try:
        with open(f"modules/infra/admin_piccolo/api-docs/{page}.md", "r") as f:
            md_data = f.read()
    except FileNotFoundError as exc:
        return {"resp": "docs", "detail": f"api-docs/{page}.md not found -> {exc}"}

    # Inject rating code if plat != DOCREADER
    if ws.state.plat != "DOCREADER":
        md_data = f"""

<div id='feedback-div'>

### Feedback

Just want to provide feedback? [Rate this page](#rate-this-page)

</div>

{md_data}

### Rate this page!

- Your feedback allows Fates List to improve our docs. 
- We would also *love* it you could make a Pull Request at [https://github.com/Fates-List/infra](https://github.com/Fates-List/infra)
- Starring the repo is also a great way to show your support!

<label for='doc-feedback'>Your Feedback</label>
<textarea 
id="doc-feedback"
name="doc-feedback"
class="form-control"
placeholder="I feel like X, Y and Z could change because..."
></textarea>

<button onclick='rateDoc()'>Rate</button>

### [View Source](https://lynx.fateslist.xyz/docs-src/{page})
        """

    # If looking for source
    if source:
        print("Sending source")
        return {
            "resp": "docs",
            "title": page.split('/')[-1].replace('-', ' ').title() + " (Source)",
            "data": f"""
    <pre>{md_data.replace('<', '&lt').replace('>', '&gt')}</pre>
            """ if ws.state.plat != "DOCREADER" else md_data,
        }

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {
        "resp": "docs",
        "title": page.split('/')[-1].replace('-', ' ').title(),
        "data": md.render(md_data).replace("<table", "<table class='table'").replace(".md", ""),
    }

@ws_action("eternatus")
async def docs_feedback(ws: WebSocket, data: dict):
    if len(data.get("feedback", "")) < 5:
        return {"resp": "eternatus", "detail": "Feedback must be greater than 10 characters long!"}

    if ws.state.user:
        user_id = int(ws.state.user["id"])
        username = ws.state.user["username"]
    else:
        user_id = None
        username = "Anonymous"

    if not data.get("page", "").startswith("/"):
        return {"resp": "eternatus", "detail": "Unexpected page!"}

    await app.state.db.execute(
        "INSERT INTO lynx_ratings (feedback, page, username_cached, user_id) VALUES ($1, $2, $3, $4)",
        data["feedback"],
        data["page"],
        username,
        user_id
    )

    return {"resp": "eternatus", "detail": "Successfully rated"}

@ws_action("cosmog")
async def verify_code(ws: WebSocket, data: dict):
    code = data.get("code", "")

    if not ws.state.user:
        return

    if ws.state.verified:
        return {
            "resp": "cosmog",
            "detail": "You are already verified"
        }

    if not code_check(code, int(ws.state.user["id"])):
        return {"resp": "cosmog", "detail": "Invalid code"}
    else:
        username = ws.state.user["username"]
        password = get_token(96)

        try:
            await app.state.db.execute("DELETE FROM piccolo_user WHERE username = $1", username)
            await BaseUser.create_user(
                username=username,
                password=password,
                email=username + "@fateslist.xyz",
                active=True,
                admin=True
            )
        except:
            return {"resp": "cosmog", "detail": "Failed to create user on lynx. Please contact Rootspring#6701"}

        await app.state.db.execute(
            "UPDATE users SET staff_verify_code = $1 WHERE user_id = $2",
            code,
            int(ws.state.user["id"]),
        )

        await add_role(staff_server, ws.state.user["id"], access_granted_role, "Access granted to server")
        await add_role(staff_server, ws.state.user["id"], ws.state.member.staff_id, "Gets corresponding staff role")

        return {"resp": "cosmog", "detail": "Successfully verified staff member", "pass": password}

@ws_action("index")
async def index(_, __):
    return {
        "resp": "index", 
        "title": "Welcome To Lynx", 
        "data": """
<h3>Homepage!</h3>
By continuing, you agree to:
<ul>
<li>Abide by Discord ToS</li>
<li>Abide by Fates List ToS</li>
<li>Agree to try and be at least partially active on the list</li>
<li>Be able to join group chats (group DMs) if required by Fates List Admin+</li>
</ul>
If you disagree with any of the above, you should stop now and consider taking a 
Leave Of Absence or leaving the staff team though we hope it won't come to this...
<br/><br/>

Please <em>read</em> the staff guide carefully. Do NOT just Ctrl-F. If you ask questions
already in the staff guide, you will just be told to reread the staff guide!

<br/>

In case, you haven't went through staff verification and you somehow didn't get redirected to it, click <a href="/staff-verify">here</a> 
<br/><br/>
<a href="/links">Some Useful Links!</a>
                """}

@ws_action("perms")
async def perms(ws: WebSocket, _):
    return {"resp": "perms", "data": ws.state.member.dict()}

@ws_action("reset")
async def reset(ws: WebSocket, _):
    # Remove from db
    if ws.state.user:
        await app.state.db.execute(
            "UPDATE users SET api_token = $1, staff_verify_code = NULL WHERE user_id = $2",
            get_token(132),
            int(ws.state.user["id"])
        )
        await app.state.db.execute(
            "DELETE FROM piccolo_user WHERE username = $1",
            ws.state.user["username"]
        )
        return {"resp": "reset", "data": None}

@ws_action("reset_page")
async def reset_page(_, __):
    return {
        "resp": "reset_page",
        "title": "Lynx Credentials Reset",
        "pre": "/links",
        "data": f"""
        <p>If you're locked out of your discord account or otherwise need to reset your credentials, just click the 'Reset' button. It will do the same
        thing as <strong>/lynxreset</strong> used to</p>

        <div id="verify-parent">
            <button id="verify-btn" onclick="reset()">Reset</button>
        </div>
        """,
        "script": """
            async function reset() {
                document.querySelector("#verify-btn").innerText = "Resetting...";

                wsSend({request: "reset"})
            }
        """
    }

@ws_action("links")
async def links(ws: WebSocket, _):
    if ws.state.member.perm > 2:
        return {
            "resp": "links",
            "title": "Some Useful Links",
            "data": f"""
            <blockquote class="quote">
                <h5>Some Nice Links</h5>
                <a href="/my-perms">My Permissions</a><br/>
                <a href="/reset">Lynx Credentials Reset</a><br/>
                <a href="/loa">Leave Of Absense</a><br/>
                <a href="/staff-apps">Staff Applications</a><br/>
                <a href="/links">Some Useful Links</a><br/>
                <a href="/staff-verify">Staff Verification</a> (in case you need it)<br/>
                <a href="/staff-guide">Staff Guide</a><br/>
                <a href="/docs/roadmap">Our Roadmap</a><br/>
                <a href="/admin">Admin Console</a><br/>
                <a href="/bot-actions">Bot Actions</a><br/>
                <a href="/user-actions">User Actions</a><br/>
                <a href="/requests">Requests</a><br/>
            </blockquote>
            <blockquote class="quote">
                <h5 id="credits">Credits</h5>
                <p>Special Thanks to <strong><a href="https://adminlte.io/">AdminLTE</a></strong> for thier awesome contents!
                </p>
            </blockquote>
        """}
    else:
        return {
            "resp": "links",
            "title": "Some Useful Links",
            "data": f"""
            <blockquote class="quote">
                <h5>Some Nice Links</h5>
                <strong>Some links hidden as you are not logged in or are not staff</strong>
                <a href="/my-perms">My Permissions</a><br/>
                <a href="/links">Some Useful Links</a><br/>
                <a href="/staff-guide">Staff Guide</a><br/>
                <a href="/docs/roadmap">Our Roadmap</a><br/>
                <a href="/requests">Requests</a><br/>
            </blockquote>
            <blockquote class="quote">
                <h5 id="credits">Credits</h5>
                <p>Special Thanks to <strong><a href="https://adminlte.io/">AdminLTE</a></strong> for thier awesome contents!
                </p>
            </blockquote>
        """}

@ws_action("user_action")
async def user_action(ws: WebSocket, data: dict):
    try:
        action = app.state.user_actions[data["action"]]
    except:
        return {"resp": "user_action", "detail": "Action does not exist!"}
    try:
        action_data = UserActionWithReason(**data["action_data"])
    except Exception as exc:
        return {"resp": "user_action", "detail": f"{type(exc)}: {str(exc)}"}
    return await action(ws, action_data)

@ws_action("bot_action")
async def bot_action(ws: WebSocket, data: dict):
    try:
        action = app.state.bot_actions[data["action"]]
    except:
        return {"resp": "bot_action", "detail": "Action does not exist!"}
    try:
        action_data = ActionWithReason(**data["action_data"])
    except Exception as exc:
        return {"resp": "bot_action", "detail": f"{type(exc)}: {str(exc)}"}
    return await action(ws, action_data)

@ws_action("request_logs")
async def request_logs(ws: WebSocket, _):
    requests = await app.state.db.fetch("SELECT user_id, method, url, status_code, request_time from lynx_logs")
    requests_html = ""
    for request in requests:
        requests_html += f"""
<p>{request["user_id"]} - {request["method"]} - {request["url"]} - {request["status_code"]} - {request["request_time"]}</p>
        """

    return {
        "resp": "request_logs",
        "title": "Lynx Request Logs",
        "pre": "/links",
        "data": f"""
        {requests_html}
        """
    }

@ws_action("data_request")
async def data_request(ws: WebSocket, data: dict):
    user_id = data.get("user", None)

    if not ws.state.user:
        return {
            "resp": "data_request",
            "detail": "You must be logged in first!"
        }

    if ws.state.member.perm < 7 and ws.state.user["id"] != user_id:
        return {
            "resp": "data_request",
            "detail": "You must either have permission level 6 or greater or the user id requested must be the same as your logged in user id."
        }

    try:
        user_id = int(user_id)
    except:
        return {
            "resp": "data_request",
            "detail": "Invalid User ID"
        }

    user = await app.state.db.fetchrow("select * from users where user_id = $1", user_id)
    owners = await app.state.db.fetch("SELECT * FROM bot_owner WHERE owner = $1", user_id)
    bot_voters = await app.state.db.fetch("SELECT * FROM bot_voters WHERE user_id = $1", user_id)
    user_vote_table = await app.state.db.fetch("SELECT * FROM user_vote_table WHERE user_id = $1", user_id)
    reviews = await app.state.db.fetch("SELECT * FROM reviews WHERE user_id = $1", user_id)
    review_votes = await app.state.db.fetch("SELECT * FROM review_votes WHERE user_id = $1", user_id)
    user_bot_logs = await app.state.db.fetch("SELECT * FROM user_bot_logs WHERE user_id = $1", user_id)
    user_payments = await app.state.db.fetch("SELECT * FROM user_payments WHERE user_id = $1", user_id)
    servers = await app.state.db.fetch("SELECT * FROM servers WHERE owner_id = $1", user_id)
    lynx_apps = await app.state.db.fetch("SELECT * FROM lynx_apps WHERE user_id = $1", user_id)
    lynx_logs = await app.state.db.fetch("SELECT * FROM lynx_logs WHERE user_id = $1", user_id)
    lynx_notifications = await app.state.db.fetch("SELECT * FROM lynx_notifications, unnest(acked_users) AS "
                                                    "user_id WHERE user_id = $1", user_id)
    lynx_ratings = await app.state.db.fetch("SELECT * FROM lynx_ratings WHERE user_id = $1", user_id)

    data = {"user": user, "owners": owners, "bot_voters": bot_voters, "user_vote_table": user_vote_table,
            "reviews": reviews, "review_votes": review_votes, "user_bot_logs": user_bot_logs,
            "user_payments": user_payments, "servers": servers,
            "lynx_apps": lynx_apps, "lynx_logs": lynx_logs, "lynx_notifications": lynx_notifications,
            "lynx_ratings": lynx_ratings, "owned_bots": [],
            "privacy": "Fates list does not profile users or use third party cookies for tracking other than what "
                        "is used by cloudflare for its required DDOS protection"}

    for bot in data["owners"]:
        data["owned_bots"].append(await app.state.db.fetch("SELECT * FROM bots WHERE bot_id = $1", bot["bot_id"]))

    return {
        "resp": "data_request",
        "user": str(user_id),
        "data": data
    }

@ws_action("data_deletion")
async def data_deletion(ws: WebSocket, data: dict):
    user_id = data.get("user", None)

    if not ws.state.user:
        return {
            "resp": "data_deletion",
            "detail": "You must be logged in first!"
        }

    if ws.state.member.perm < 7 and ws.state.user["id"] != user_id:
        return {
            "resp": "data_deletion",
            "detail": "You must either have permission level 6 or greater or the user id requested must be the same as your logged in user id."
        }

    try:
        user_id = int(user_id)
    except:
        return {
            "resp": "data_deletion",
            "detail": "Invalid User ID"
        }

    print("[LYNX] Wiping user info in db")
    await app.state.db.execute("DELETE FROM users WHERE user_id = $1", user_id)

    bots = await app.state.db.fetch(
        """SELECT DISTINCT bots.bot_id FROM bots 
        INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
        WHERE bot_owner.owner = $1 AND bot_owner.main = true""",
        user_id,
    )
    for bot in bots:
        await app.state.db.execute("DELETE FROM bots WHERE bot_id = $1", bot["bot_id"])
        await app.state.db.execute("DELETE FROM vanity WHERE redirect = $1", bot["bot_id"])

    votes = await app.state.db.fetch(
        "SELECT bot_id from bot_voters WHERE user_id = $1", user_id)
    for vote in votes:
        await app.state.db.execute(
            "UPDATE bots SET votes = votes - 1 WHERE bot_id = $1",
            vote["bot_id"])

    await app.state.db.execute("DELETE FROM bot_voters WHERE user_id = $1", user_id)

    print("[LYNX] Clearing redis info on user...")
    await app.state.redis.hdel(str(user_id), "cache")
    await app.state.redis.hdel(str(user_id), "ws")

    await app.state.redis.close()

    return {
        "resp": "data_deletion",
        "detail": "All found user data deleted"
    }

@ws_action("survey_list")
async def survey(ws: WebSocket, _):
    surveys = await app.state.db.fetch("SELECT id, title, questions FROM lynx_surveys")
    surveys_html = ""
    for survey in surveys:
        questions = orjson.loads(survey["questions"])

        if not isinstance(questions, list):
            continue

        questions_html = ''
        question_ids = []
        for question in questions:
            if not question.get("question") or not question.get("type") or not question.get("id") or not question.get("textarea"):
                continue
            questions_html += f"""
<div class="form-group">
<label id="{question["id"]}-label">{question["question"]}</label>
<{"input" if not question["textarea"] else "textarea"} class="form-control" placeholder="Minimum of 6 characters" minlength="6" required="true" aria-required="true" id="{question["id"]}" type="{question["type"]}" name="{question["id"]}"></{"input" if not question["textarea"] else "textarea"}>
</div>
            """
            question_ids.append(str(question["id"]))

        surveys_html += f"""
::: survey

### {survey["title"]}

{questions_html}

<button onclick="submitSurvey('{str(survey["id"])}', {question_ids})">Submit</button>

:::
    """

    md = (
        MarkdownIt()
            .use(front_matter_plugin)
            .use(footnote_plugin)
            .use(anchors_plugin, max_level=5, permalink=True)
            .use(fieldlist_plugin)
            .use(container_plugin, name="warning")
            .use(container_plugin, name="info")
            .use(container_plugin, name="aonly")
            .use(container_plugin, name="guidelines")
            .use(container_plugin, name="generic", validate=lambda *args: True)
            .enable('table')
            .enable('image')
    )

    return {"resp": "survey_list", "title": "Survey List", "pre": "/links", "data": md.render(surveys_html), "ext_script": "surveys"}

@ws_action("survey")
async def submit_survey(ws: WebSocket, data: dict):
    id = data.get("id", "0")
    answers = data.get("answers", {})

    questions = await app.state.db.fetchval("SELECT questions FROM lynx_surveys WHERE id = $1", id)
    if not questions:
        return {"resp": "survey", "detail": "Survey not found"}
    
    questions = orjson.loads(questions)

    if len(questions) != len(answers):
        return {"resp": "survey", "detail": "Invalid survey. Refresh and try again"}

    await app.state.db.execute(
        "INSERT INTO lynx_survey_responses (survey_id, questions, answers, user_id, username_cached) VALUES ($1, $2, $3, $4, $5)",
        id,
        orjson.dumps(questions).decode(),
        orjson.dumps(answers).decode(),
        int(ws.state.user["id"]) if ws.state.user else None,
        ws.state.user["username"] if ws.state.user else "Anonymous"
    )
    return {"resp": "survey", "detail": "Submitted survey"}

print(ws_action_dict)

async def do_task_and_send(f, ws, data):
    ret = await f(ws, data)
    await manager.send_personal_message(ret, ws)

async def out_of_date(ws):
    await manager.connect(ws)
    await manager.send_personal_message({"resp": "spld", "e": SPLDEvent.out_of_date}, ws)
    await asyncio.sleep(0.3)
    await ws.close(4008)

def replace_if_web(msg, ws):
    if ws.state.plat == "WEB":
        return msg.replace("<", "&lt").replace(">", "&gt")
    return msg

# Cli = client, plat = platform (WEB or SQUIRREL)
@app.websocket("/_ws")
async def ws(ws: WebSocket, cli: str, plat: str):
    if ws.headers.get("Origin") != "https://lynx.fateslist.xyz" and plat != "DOCREADER":
        print(f"Ignoring malicious websocket request with origin {ws.headers.get('Origin')}")
        return
    
    if plat not in ("WEB", "SQUIRREL", "DOCREADER"):
        print("Client out of date, invalid platform")

        ws.state.debug = False
        return await out_of_date(ws)
    
    if plat in ("SQUIRREL", "DOCREADER"):
        ws.state.debug = True # Squirrel and docreader doesnt support no-debug mode *yet*
    else:
        ws.state.debug = False
    
    ws.state.cli = cli
    ws.state.plat = plat

    try:
        cli, _time = cli.split("@")
    except:
        print("Client out of date, invalid cli")

        ws.state.debug = False
        return await out_of_date(ws)

    # Check nonce to ensure client is up to date
    if (ws.state.plat == "WEB" and cli != "Comfreys"  # TODO, obfuscate/hide nonce in core.js and app.py
        or (ws.state.plat == "SQUIRREL" and cli != "BurdockRoot")
        or (ws.state.plat == "DOCREADER" and cli != "Quailfeather")
    ):
        print("Client out of date, nonce incorrect")

        ws.state.debug = False
        return await out_of_date(ws)
    
    if ws.state.plat in ("WEB", "DOCREADER"):
        if not _time.isdigit():
            print("Client out of date, nonce incorrect")

            ws.state.debug = False
            return await out_of_date(ws)
        elif time.time() - int(_time) > 20:
            print("Network connection too slow!")

            ws.state.debug = False
            return await out_of_date(ws)


    ws.state.user = None
    ws.state.member = StaffMember(name="Unknown", id=0, perm=-1, staff_id=0)
    ws.state.token = "Unknown"

    await manager.connect(ws)

    if ws.state.plat == "WEB":
        await manager.send_personal_message({
            "resp": "cfg", 
            "assets": {
                "bot-actions": "/_static/bot-actions.js?v=74",
                "user-actions": "/_static/user-actions.js?v=73",
                "surveys": "/_static/surveys.js?v=72",
                "apply": "/_static/apply.js?v=79",
            },
            "responses": ['docs', 'links', 'staff_guide', 'index', "request_logs", "reset_page", "staff_apps", "loa", "user_actions", "bot_actions", "staff_verify", "survey_list", "get_sa_questions"],
            "actions": ['user_action', 'bot_action', 'eternatus', 'survey', 'data_deletion', 'apply_staff', 'send_loa']
        }, ws)

    if ws.cookies.get("sunbeam-session:warriorcats") and ws.state.plat != "DOCREADER":
        print(f"WS Cookies: {ws.cookies}")
        try:
            sunbeam_user = orjson.loads(b64decode(ws.cookies.get("sunbeam-session:warriorcats")))
            data = await app.state.db.fetchrow(
                "SELECT api_token, staff_verify_code FROM users WHERE user_id = $1 AND api_token = $2",
                int(sunbeam_user["user"]["id"]),
                sunbeam_user["token"]
            )
            if not data:
                await ws.close(4008)
                return

            ws.state.token = data["api_token"]
            if not ws.state.token:
                await ws.close(4008)
                return

            ws.state.user = await fetch_user(int(sunbeam_user["user"]["id"]))

            _, _, ws.state.member = await is_staff(int(sunbeam_user["user"]["id"]), 2)
            await manager.send_personal_message({"resp": "perms", "data": ws.state.member.dict()}, ws)
            await manager.send_personal_message({"resp": "user_info", "user": ws.state.user}, ws)
            ws.state.verified = True

            if not code_check(data["staff_verify_code"], int(sunbeam_user["user"]["id"])) and ws.state.member.perm >= 2:
                await manager.send_personal_message({"resp": "spld", "e": SPLDEvent.verify_needed}, ws)  # Request staff verify
                ws.state.verified = False

        except Exception as exc:
            # Let them stay unauthenticated
            print(exc)
            pass

    try:
        while True:
            try:
                if ws.state.debug:
                    data = await ws.receive_json()
                else:
                    data = msgpack.unpackb(await ws.receive_bytes())
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    return
                print(f"{type(exc)}: {exc}")
                continue
        
            if ws.state.debug or data.get("request") not in ("notifs",):
                print(data)

            if ws.state.user is not None:
                # Check perms as this user is logged in
                check = await app.state.db.fetchrow(
                    "SELECT user_id, staff_verify_code FROM users WHERE user_id = $1 AND api_token = $2",
                    int(ws.state.user["id"]),
                    ws.state.token
                )
                if not check:
                    print("Invalid token")
                    await ws.close(code=1008)
                    return

                _, _, member = await is_staff(int(ws.state.user["id"]), 2)

                if ws.state.member.perm != member.perm:
                    ws.state.member = member
                    await manager.send_personal_message({"resp": "perms", "data": ws.state.member.dict()}, ws)

                if ws.state.verified and not code_check(check["staff_verify_code"], int(sunbeam_user["user"]["id"])):
                    ws.state.verified = False
            
            try:
                if ws.state.plat == "SQUIRREL" and data.get("request") not in ("bot_action", "user_action"):
                    print("[LYNX] Warning: Unsupported squirrel action")
                    await manager.send_personal_message({"resp": "spld", "e": SPLDEvent.unsupported}, ws)
                    continue
                elif ws.state.plat == "DOCREADER" and data.get("request") not in ("docs", "doctree"):
                    print("[LYNX] Warning: Unsupported docreader action")
                    await manager.send_personal_message({"resp": "spld", "e": SPLDEvent.unsupported}, ws)
                    continue

                f = ws_action_dict.get(data.get("request"))
                if not f:
                    print(f"could not find {data}")
                else:
                    asyncio.create_task(do_task_and_send(f, ws, data))
            except Exception as exc:
                print(exc)

    except WebSocketDisconnect:
        manager.disconnect(ws)


class UserActionWithReason(BaseModel):
    user_id: str
    initiator: int | None = None
    reason: str
    context: Any | None = None


app.state.user_actions = {}


def user_action(
        name: str,
        states: list[enums.UserState],
        min_perm: int = 2,
):
    async def state_check(bot_id: int):
        user_state = await app.state.db.fetchval("SELECT state FROM users WHERE user_id = $1", bot_id)
        return (user_state in states) or len(states) == 0

    async def _core(ws: WebSocket, data: UserActionWithReason):
        if ws.state.member.perm < min_perm:
            return {
                "resp": "user_action",
                "detail": f"PermError: {min_perm=}, {ws.state.member.perm=}"
            }
        
        data.initiator = int(ws.state.user["id"])

        if not data.user_id.isdigit():
            return {
                "resp": "user_action",
                "detail": "User ID is invalid"
            }

        data.user_id = int(data.user_id)

        if not await state_check(data.user_id):
            return {
                "resp": "user_action",
                "detail": replace_if_web(f"User state check error: {states=}", ws)
            }

    def decorator(function):
        async def wrapper(ws, data: UserActionWithReason):
            if _data := await _core(ws, data):
                return _data # Exit if true, we've already sent
            if len(data.reason) < 5:
                return {
                    "resp": "user_action",
                    "detail": "Reason must be more than 5 characters"
                }
            res = await function(data)
            res = jsonable_encoder(res)
            res["resp"] = "user_action"

            err = res.get("err", False)

            if not err:
                spl = res.get("spl", True)

                if spl:
                    # Tell client that a refresh is needed as a user action has taken place
                    await manager.broadcast({"resp": "spld", "e": SPLDEvent.refresh_needed, "loc": "/user-actions"})


            return res

        app.state.user_actions[name] = wrapper
        return wrapper

    return decorator


### Client should lie here and give a generic reason for add_staff

@user_action("add_staff", [enums.UserState.normal], min_perm=5)
async def add_staff(data: UserActionWithReason):
    await add_role(main_server, data.user_id, staff_roles["community_staff"]["id"], "New staff member")
    await add_role(main_server, data.user_id, staff_roles["bot_reviewer"]["id"], "New staff member")

    # Check if DMable by attempting to send a message
    async with aiohttp.ClientSession() as sess:
        async with sess.post(
                "https://discord.com/api/v10/users/@me/channels",
                json={"recipient_id": str(data.user_id)},
                headers={"Authorization": f"Bot {main_bot_token}"}) as res:
            if res.status != 200:
                json = await res.json()
                return {
                    "detail": f"User is not DMable {json}",
                    "err": True
                }
            json = await res.json()
            channel_id = json["id"]

        embed = Embed(
            color=0xe74c3c,
            title="Staff Application Accepted",
            description=f"You have been accepted into the Fates List Staff Team!",
        )

        res = await send_message({
            "channel_id": channel_id,
            "embed": embed,
            "content": """
Please join our staff server first of all: https://fateslist.xyz/banappeal/invite

Then head on over to https://lynx.fateslist.xyz to read our staff guide and get started!
            """
        })

        if not res.ok:
            return {
                "detail": f"Failed to send message (possibly blocked): {res.status}",
                "err": True
            }

    return {"detail": "Successfully added staff member"}


### Client should lie here and give a generic reason for ack_staff_app

@user_action("ack_staff_app", [], min_perm=4)
async def ack_staff_app(data: UserActionWithReason):
    await app.state.db.execute("DELETE FROM lynx_apps WHERE user_id = $1", data.user_id)
    # Special broadcast for Acking
    await manager.broadcast({"resp": "spld", "e": SPLDEvent.refresh_needed, "loc": "/staff-apps"})
    return {"detail": "Acked", "spl": False}


@user_action("set_user_state", [], min_perm=4)
async def set_user_state(data: UserActionWithReason):
    if not isinstance(data.context, int):
        return {"detail": "State must be an integer", "err": True}
    try:
        state = enums.UserState(data.context)
    except:
        return {"detail": "State must be of enum UserState", "err": True}

    await app.state.db.fetchval("UPDATE users SET state = $1 WHERE user_id = $2", state, data.user_id)

    embed = Embed(
        url=f"https://fateslist.xyz/profile/{data.user_id}",
        color=0xe74c3c,
        title="User State Updated",
        description=f"<@{data.initiator}> has modified the state of <@{data.user_id}> with new state of {state.name} ({state.value}) -> {state.__doc__} !\n\nThank you for using Fates List and we are sorry for any inconveniences caused :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await send_message({"content": f"<@{data.user_id}>", "embed": embed, "channel_id": bot_logs})

    return {"detail": "Successfully set user state"}


print(app.state.user_actions)
print(app.state.bot_actions)


@app.on_event("startup")
async def startup():
    signal.signal(signal.SIGINT, handle_kill)
    engine = engine_finder()
    app.state.engine = engine
    app.state.redis = aioredis.from_url("redis://localhost:1001", db=1)
    app.state.db = await asyncpg.create_pool()
    await engine.start_connection_pool()


def handle_kill(*args, **kwargs):
    async def _close():
        await asyncio.sleep(0)
        await manager.broadcast({"resp": "spld", "e": SPLDEvent.maint})

    print("Broadcasting maintenance")
    asyncio.create_task(_close())

@app.on_event("shutdown")
async def close():
    await app.state.engine.close_connection_pool()


app.add_middleware(CustomHeaderMiddleware)
