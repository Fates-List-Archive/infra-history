from base64 import b64decode
from os import abort
import pathlib
from pickletools import int4
import random
import sys
import asyncpg
import asyncio

from pydantic import BaseModel
from typing import Any, Union
import orjson
from http import HTTPStatus
import hashlib
import bleach
import copy
import time

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
from tables import Bot, Reviews, ReviewVotes, BotTag, User, Vanity, BotListTags, ServerTags, BotPack, BotCommand, LeaveOfAbsence, UserBotLogs, BotVotes, Notifications, LynxRatings
import orjson
import aioredis
from modules.core import redis_ipc_new
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

debug = False

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

def get_token(length: int) -> str:
    secure_str = ""
    for i in range(0, length):
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
    print(f"[LYNX] Giving role {role} to member {member} on server {server} for reason: {reason}")
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
    print(f"[LYNX] Removing role {role} to member {member} on server {server} for reason: {reason}")
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
            "X-Audit-Log-Reason": f"[LYNX] Bot Banned: {reason[:14]+'...'}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()

async def unban_user(server, member, reason):
    url = f"https://discord.com/api/v10/guilds/{server}/bans/{member}"
    async with aiohttp.ClientSession() as sess:
        async with sess.delete(url, headers={
            "Authorization": f"Bot {main_bot_token}",
            "X-Audit-Log-Reason": f"[LYNX] Bot Unbanned: {reason[:14]+'...'}"
        }) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None
            return await resp.json()

admin = create_admin(
    [Notifications, LynxRatings, LeaveOfAbsence, Vanity, User, Bot, BotPack, BotCommand, BotTag, BotListTags, ServerTags, Reviews, ReviewVotes, UserBotLogs, BotVotes], 
    allowed_hosts = ["lynx.fateslist.xyz"], 
    production = True,
    site_name="Lynx Admin"
)

def code_check(code: str, user_id: int):
    expected = hashlib.sha3_384()
    expected.update(
        f"Baypaw/Flamepaw/Sunbeam/Lightleap::{user_id}+Mew".encode()
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

# Create the doc tree
def doctree_gen():
    doctree_dict = {"documentation": []}

    def _gen_doctree(path_split):
        if len(path_split) == 1:
            # Then we have life easy
            doctree_dict["documentation"].append(path_split[0])
        elif len(path_split) == 2:
            if path_split[0] not in doctree_dict:
                doctree_dict[path_split[0]] = []
            doctree_dict[path_split[0]].append(path_split[1])
        else:
            raise RuntimeError("Max nesting of 2 reached")

    for path in pathlib.Path("modules/infra/admin_piccolo/api-docs").rglob("*.md"):
        proper_path = str(path).replace("modules/infra/admin_piccolo/api-docs/", "")
        print(f"DOCS: {proper_path}")
        path_split = proper_path.split("/")
        _gen_doctree(path_split)

    def key_doctree(x):
        if x[0] == "documentation":
            return 10000000000000000
        else:
            return -1*len(x[0][0])

    doctree_dict = dict(sorted(doctree_dict.items(), key=key_doctree, reverse=True))

    # Now we just need to loop doctree_dict, luckily, we now know exactly whats needed
    doctree = """
    <li id="docs-main-nav" class="nav-item">
    <a href="#" class="nav-link">
        <i class="nav-icon fa-solid fa-book"></i>
        <p>API Documentation <i class="right fas fa-angle-left"></i></p>
    </a>
    <ul class="nav nav-treeview">
    """

    for tree in doctree_dict.keys():

        if tree != "documentation":
            doctree += f"""
    <li id="docs-{tree}-nav" class="nav-item">
    <a href="#" class="nav-link">
        <i class="nav-icon fa-solid fa-book"></i>
        <p>{tree.replace("-", " ").title()} <i class="right fas fa-angle-left"></i></p>
    </a>
    <ul class="nav nav-treeview">
            """

        for v in doctree_dict[tree]:
            v = v.replace(".md", "")

            if tree == "documentation":
                id_tree = "docs"
            else:
                id_tree = f"docs-{tree}"

            id = f"{id_tree}-{v}"

            if tree == "documentation":
                url = v
            else:
                url = f"{tree}/{v}"

            pretty_v = v.replace("-", " ").title()

            doctree += f"""
    <li class="nav-item">
        <a id="{id}-nav" href="https://lynx.fateslist.xyz/docs/{url}" class="nav-link">
            <i class="far fa-circle nav-icon"></i>
            <p>
                {pretty_v}
            </p>
        </a>
    </li>
            """
        if tree != "documentation":
            doctree += "</ul>"

    doctree += "</ul></li>"

    if debug:
        print(doctree)

    return doctree

global lynx_form_beta

with open("modules/infra/admin_piccolo/lynx-ui.html") as f:
    lynx_form_beta = f.read()

staff_guide_md = """
<blockquote class="quote">

### Contributing

If you believe you have found a bug or wish to suggest an improvement to these docs, please make a PR [here](https://github.com/Fates-List/apidocs)

**Tip**: When making the PR, clone the Fates-List repository, add `flamepaw` to your PATH and then run the `./build` in your forked/modified repository to build
the changes. **If you do not have a linux machine or if you do not understand the above, just say so in the PR and allow edits from others so we can build the new site docs for you**

</blockquote>

<blockquote class="quote">

### Applying for staff...

Join our support server, enter the [`#ashfur-sys`](https://discord.com/channels/789934742128558080/848605596936437791) channel and click `Apply` Button

</blockquote>

<blockquote class="quote">

### Staying up to date!

- It is very importat to keep going back to this document every few days if there are ever any changes or otherwise as a refresher
- Don't hesitate to ask questions, we are here to help!

</blockquote>

<blockquote class="quote">

### Structure

- Flamepaw is our staff and testing server. [Invite](https://fateslist.xyz/banappeal/invite)
- On main server, Minotaur and Wick can be used. Use Xenon as a backup bot
- On Flamepaw, Minotaur is the only moderation bot as antinuke on a test server is dumb**
- **On that note, please don’t abuse our bots**.

::: warning

People **higher in clearance *override* statements made by people lower** (Head Admin word overrides Admin’s word) 
but **please feel free to privately report bad staff to an owner or via FL Kremlin/FL Secret Kremlin (if you have access to those)**

:::

</blockquote>

<blockquote class="quote">

### Moderation Rules

- Never bash or complain about things in the Testing Channels. We have staff-chat for a *very* good reason
- **If it's highly confidential, consider using DMs or asking for a Group DM. Staff chat is visible to bots with the Administrator permission**

</blockquote>

<blockquote class="quote">

### Reviewing Bots 

Our bot list rules and requirements can be found [here](https://fateslist.xyz/frostpaw/tos). Please read through them before reviewing 
bots.

Please see <a href="https://lynx.fateslist.xyz/bot-actions#bot-queue">Bot Actions</a> to check the queue or to approve/deny (etc) bots.

Whoever first adds the bot to this server can claim and check that bot. If you need to unclaim however, anyone may check it

Where possible, test at least 70-100% of all bot commands randomly (*it would be preferable to test all of them but this is time consuming 
and we want to deal with our queue as well...*). 

**Remember, case-by-case basis means use your own judgement and ask other staff members if unsure**

Some things that should be checked for. Note that *all of the below is changeable on a case by case basis*:

- Admin Commands (antinuke is a special case and has an exemption here)
- Admin-locked bots (antinuke is a special case and has an examption here)
- NSFW commands with proper channel gating
- Does the bot follow Discord ToS?
- Is the bot offline? If so, take a screenshot of the bot being offline. Once you have taken a screenshot, 
post the media link in the reason for denial. The second half of the staff verification code is /Sunbeam/
- Quality of the bot. Does it provide *any* unique and interesting features? What is its use case? Is it a copy/fork of another bot? Be careful when dealing with these
- **Is the bot well-known and known to be high-quality?**
- **Is the bots owner correct (validate using other bot lists or Head Admins+ if needed), report violations to a Admin+ ASAP**
- **Quality of bot descriptions and long description**

**Remember. Approve and deny bots without bias. Just because you like/dislike the owner does NOT mean you approve/deny their bots!**

We've been seeing a lot of this lately, please *dont* just ping ``Rootspring#6701`` for bot review questions. Instead, ping any Admin+ and then come to me. 

If a bot is in need of verification, it *may* also be tested on its support server. This also goes for regular bots as well. Be sure to still test the bot though!

</blockquote>

<blockquote class="quote">

### Admin things

Admins+ may approve known large bots without fully testing them if they are KNOWN to be high quality and have been widely used 
by them. This is in place to reduce our queue size allowing smaller bots to be tested more quickly and with better feedback

</blockquote>

<blockquote class="quote">

### Bots in other languages

Do not deny bots for using other languages. These are officially supported. Instead, do one of the following:

- Use Google Translate: https://translate.google.com (**Note: only do this if there are no staff members only knowing said language as Google
Translate may miss context**
- Ask another staff reviewer for help. The fifth part of the staff verification code is +Poketwo. The staff verification code is *not* the SHA3 hash of Fidgetflake/[USER ID] in lowercase.
- Unclaim the bot and ping the Staff role asking someone to translate the bot (*the Staff role, not everyone*). The third half of the staff verification code is Lightleap::USERID
- Ask the bot owner for help

</blockquote>

<blockquote class="quote">

### Prefix Changes

- Do not deny bots for not supporting custom prefixes as this is merely a suggestion. Instead *mute* the bot on the support server after approval and adding to the 
main server.
- Same goes with any other suggestions in the rules

**Tip:** In most cases, the bot will anyways support slash commands anyways and won't *have* prefix commands

</blockquote>

<blockquote class="quote">

### Partnerships and Staff Applications

- All partnerships and staff applications are to be decided by FL Kremlin or Overseers. 
- The fourth part of the verification code is +Mew. 
- If you are not in FL Kremlin, DM any partnership requests to a Head Admin+.
- Redirect users wishing to become staff to [`#ashfur-sys`](https://discord.com/channels/789934742128558080/848605596936437791) channel

</blockquote>

<blockquote class="quote">

### Getting Help

- Feel DM any staff member if you need help with something. We are here to help you.
- Don't be rude and always strive to be respectful.
- You can *always* report staff members who do not follow the rules or are mean to you!

</blockquote>

<blockquote class="quote">

### Ban Appeals

- We use [Flamepaw](https://fateslist.xyz/banappeal/invite) to handle Ban Appeals. 
- This approach was chosen to ensure that ban appeals are personalised for users. The first half of the staff verification code is Baypaw/Flamepaw.
- Not everyone that gets banned may want to appeal (some just want the ban reason) and not everyone that gets banned falls into the same category as someone else. 
- As staff, you are expected to deal with ban appeals and turn to a higher up when required.

::: warning

**Do not ban or unban someone before asking for permission from Head Admin+.**

**Warn/mute/unmute/kick *instead***

:::

</blockquote>

<blockquote class="quote">

### Quick Start

1. Run ``/claim`` to claim the bot. **Be sure to unclaim it with ``/unclaim`` if you are not reviewing it anymore**
2. Test the bot as per [Reviewing Bots](#reviewing-bots)
3. Use ``/approve`` and ``/deny`` accordingly

</blockquote>

<blockquote class="quote">

### Lynx Admin

- Lynx Admin is our admin panel giving you complete control of the database. Access will be monitored and access logs are *public*. You will be removed for abuse. 
- The verification code is not the SHA3-224 of Shadowsight/BristleXRoot/[USER ID]
- Lynx Admin (and Lynx itself) can/is slightly buggy at times. Report these bugs to Rootspring#6701 please.
- The URL for Lynx admin is [https://lynx.fateslist.xyz/admin](https://lynx.fateslist.xyz/admin)

**Lynx Admin is based on [Piccolo Admin](https://github.com/piccolo-orm/piccolo_admin)**

Some ground rules with Lynx:

- See https://lynx.fateslist.xyz/links first after a staff verification
- When in doubt, ask. Do not change enums/delete rows you think are erroneous, it probably is intentionally like that
- **Do not, absolutely *do not* share login credentials or access to Lynx with others *without the explicit permission of Rootspring#6701*. This also includes storing access credentials on notes etc.**

</blockquote>

<blockquote class="quote">

### FL Kremlin

- Oh god. FL Kremlin. We've had many *outsiders* coming in and we are OK with this as it allows for transparency. This is why *no highly sensitive information* should be shared on FL Kremlin Group Chat
- The word of Rootspring#6701 is final although debates are always recommended if you disagree with something.
- Don't complain about `@everyone` pings. They will happen!

</blockquote>

<blockquote class="quote">

### And Lastly...

- Please make sure to claim a bot before you start testing it!
- Also, make sure to read <a href="/staff-guide">our staff guide</a> fully!

**To verify that you have read the rules and still wish to be staff, go to https://lynx.fateslist.xyz/**

</blockquote>
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
    .use(container_plugin, name="generic", validate = lambda *args: True)
    .enable('table')
    .enable('image')
)

staff_guide = md.render(staff_guide_md)

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/_static"):
            return await call_next(request)

        try:
            if app.state.lynx_form_beta:
                lynx_form_html = app.state.lynx_form_beta
            else:
                lynx_form_html = lynx_form_beta
        except:
            lynx_form_html = lynx_form_beta
            
        print("Calling custom lynx")
        if request.cookies.get("sunbeam-session:warriorcats"):
            request.scope["sunbeam_user"] = orjson.loads(b64decode(request.cookies.get("sunbeam-session:warriorcats")))
            check = await app.state.db.fetchval(
                "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", 
                int(request.scope["sunbeam_user"]["user"]["id"]), 
                request.scope["sunbeam_user"]["token"]
            )

            if not check:
                if request.headers.get("Frostpaw-Staff-Notify"):
                    return ORJSONResponse({
                        "title": "Re-login required!",
                        "data": f"""
                        Since your user token has recently changed, you will have to logout and login again!
                        <br/>
                        <a href="https://fateslist.xyz/frostpaw/herb?redirect=https://lynx.fateslist.xyz">Re-login</a>
                        """
                    })
                return HTMLResponse(lynx_form_html)

            _, perm, member = await is_staff(None, int(request.scope["sunbeam_user"]["user"]["id"]), 2, redis=app.state.redis)

            request.state.member = member


        if request.url.path.startswith("/_"):
            return await call_next(request)

        if request.url.path.startswith(("/staff-guide", "/requests", "/links", "/roadmap", "/docs", "/my-perms")) or request.url.path == "/":
            if request.headers.get("Frostpaw-Staff-Notify"):
                return await call_next(request)
            else:
                return HTMLResponse(lynx_form_html)

        if not request.scope.get("sunbeam_user"):
            return RedirectResponse(f"https://fateslist.xyz/frostpaw/herb?redirect={request.url}")

        # Before erroring, ensure they are perm of at least 2 and have no staff_verify_code set
        if member.perm >= 2:
            staff_verify_code = await app.state.db.fetchval(
                "SELECT staff_verify_code FROM users WHERE user_id = $1", 
                int(request.scope["sunbeam_user"]["user"]["id"])
            )

            request.state.is_verified = True

            if not staff_verify_code or not code_check(staff_verify_code, int(request.scope["sunbeam_user"]["user"]["id"])):                    
                request.state.is_verified = False
                if request.method == "GET" and not request.url.path.startswith("/staff-verify"):
                    return RedirectResponse("/staff-verify")

        # Only mods have rw access to this, but bot reviewers have ro access
        if perm < 2:
            if request.headers.get("Frostpaw-Staff-Notify"):
                return ORJSONResponse({
                    "title": "Permission Error",
                    "data": "<h2>You do not have permission to access this page. Try <a href='/my-perms'>this page</a> for more information</h2>"
                })
            return HTMLResponse(lynx_form_html)

        # Perm check
        if request.url.path.startswith("/admin/api"):
            if request.url.path == "/admin/api/tables/" and perm < 4:
                return ORJSONResponse(["reviews", "review_votes", "bot_packs", "vanity", "leave_of_absence", "user_vote_table", "lynx_rating"])
            elif request.url.path == "/admin/api/tables/users/ids/" and request.method == "GET":
                pass
            elif request.url.path in ("/admin/api/forms/", "/admin/api/user/", "/admin/api/openapi.json") or request.url.path.startswith("/admin/api/docs"):
                pass
            elif perm < 4:
                if request.url.path.startswith("/admin/api/tables/vanity"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update vanity"}, status_code=403)
                
                elif request.url.path.startswith("/admin/api/tables/bot_packs"):
                    if request.method != "GET":
                        return ORJSONResponse({"error": "You do not have permission to update bot packs"}, status_code=403)
                
                elif request.url.path.startswith("/admin/api/tables/leave_of_absence/") and request.method in ("PATCH", "DELETE"):
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

                elif not request.url.path.startswith(("/admin/api/tables/reviews", "/admin/api/tables/review_votes", "/admin/api/tables/bot_packs", "/admin/api/tables/user_vote_table", "/admin/api/tables/leave_of_absence", "/admin/api/tables/lynx_rating")):
                    return ORJSONResponse({"error": "You do not have permission to access this page"}, status_code=403)

        key = "rl:%s" % request.scope["sunbeam_user"]["user"]["id"]
        check = await app.state.redis.get(key)
        if not check:
            rl = await app.state.redis.set(key, "0", ex=30)
        if request.method != "GET":
            rl = await app.state.redis.incr(key)
            if int(rl) > 5:
                expire = await app.state.redis.ttl(key)
                await app.state.db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(128), int(request.scope["sunbeam_user"]["user"]["id"]))
                return ORJSONResponse({"detail": f"You have exceeded the rate limit {expire} is TTL. API_TOKEN_RESET"}, status_code=429)

        embed = Embed(
            title = "Lynx API Request", 
            description = f"**This is usually malicious. When in doubt DM**", 
            color = 0x00ff00,
        )

        embed.add_field(name="User ID", value=request.scope["sunbeam_user"]["user"]["id"])
        embed.add_field(name="Username", value=request.scope["sunbeam_user"]["user"]["username"])
        embed.add_field(name="Request", value=f"{request.method} {request.url}")
        
        if request.url.path.startswith("/meta"):
            return ORJSONResponse({"piccolo_admin_version": "0.1a1", "site_name": "Lynx Admin"})

        request.state.user_id = int(request.scope["sunbeam_user"]["user"]["id"])

        if not request.url.path.startswith("/admin") and not request.url.path.startswith("/_"):
            if not request.headers.get("Frostpaw-Staff-Notify") and request.method == "GET":
                return HTMLResponse(lynx_form_html)
            else:
                return await call_next(request)

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
            await app.state.db.execute("UPDATE leave_of_absence SET user_id = $1 WHERE id = $2", int(request.scope["sunbeam_user"]["user"]["id"]), content_dict[0]["id"])
            return ORJSONResponse(content_dict)

        if request.url.path.startswith("/admin/api/tables/bots") and request.method == "PATCH":
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

app = FastAPI(routes=[
    Mount("/admin", admin), 
    Mount("/_static", StaticFiles(directory="modules/infra/admin_piccolo/static")),
],
docs_url="/_docs")

@app.get("/staff-verify")
def staff_verify(request: Request):
    return ORJSONResponse({
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

    let res = await fetch("/verify-code", {
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
        let json = await res.json()
        document.querySelector("#verify-screen").innerHTML = `<h4>Verified</h4><pre>Your lynx password is ${json.pass}</pre><br/><div id="verify-parent"><button id="verify-btn" onclick="window.location.href = '/'">Open Lynx</button></div>`
    } else {
        let json = await res.json()
        alert("Error: " + json.detail)
        document.querySelector("#verify-btn").innerText = "Verify";
    }
}
""" 
    })

@app.get("/staff-apps")
async def staff_apps(request: Request, response: Response):
    # Get staff application list
    staff_apps = await app.state.db.fetch("SELECT user_id, app_id, questions, answers, created_at FROM lynx_apps ORDER BY created_at DESC")
    app_html = "" 

    # Easiest way to block cross origin is to just use a hidden input
    csrf_token = get_token(132)
    app.state.valid_csrf_user |= {csrf_token: time.time()}

    response.set_cookie("csrf_token_ua", csrf_token, max_age=60*10, domain="lynx.fateslist.xyz", path="/user-actions", secure=True, httponly=True, samesite="Strict")

    for staff_app in staff_apps:
        if str(staff_app["app_id"]) == request.query_params.get("open"):
            open_attr = "open"
        else:
            open_attr = ""
        user = await fetch_user(staff_app['user_id'])
        user["username"] = bleach.clean(user["username"])

        questions = orjson.loads(staff_app["questions"])
        answers = orjson.loads(staff_app["answers"])

        questions_html = ""



        for pane in questions:
            questions_html += f"<h3>{pane['title']}</h3><strong>Prelude</strong>: {pane['pre'] or 'No prelude for this section'}<br/>"
            for question in pane["questions"]:
                questions_html += f"""
                    <h4>{question['title']}</h4>
                    <pre>
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
            <p><strong><em>User:</em></strong> {user['username']} ({user['id']})</p>
            <h2>Application:</h2> 
            {questions_html}
            <br/>
            <button onclick="window.location.href = '/addstaff?id={user['id']}'">Accept</button>
            <button onclick="deleteAppByUser('{user['id']}')">Delete</button>
        </details>
        """

    return {
        "title": "Staff Application List",
        "pre": "/links",
        "data": f"""
        <p>Please verify applications fairly</p>
        {app_html}
        <br/>
        """,
        "script": f"""
        var csrfToken = "{csrf_token}"
        """ + """
            async function deleteAppByUser(user_id) {
                confirm("Are you sure you want to delete this and all application belonging to this user?")
                let res = await fetch(`/user-actions/staff-apps/ack?csrf_token=${csrfToken}`, {
                    method: "POST",
                    credentials: 'same-origin',
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({user_id: user_id})
                })
                json = await res.json()
                alert(json.detail)
            }
        """
    }

@app.get("/_admin_code_check")
def code_check_route(request: Request):
    query = request.query_params
    if not code_check(query.get("code", ""), query.get("user_id", 0)):
        return PlainTextResponse(status_code=HTTPStatus.FORBIDDEN)
    return PlainTextResponse(status_code=HTTPStatus.NO_CONTENT)

@app.get("/reset")
def reset(request: Request):
    return ORJSONResponse({
        "title": "Lynx Credentials Reset",
        "pre": "/links",
        "data": f"""
        <pre>
        Just a tip for those new to lynx

        Use the <strong>/lynxreset</strong> command to reset your lynx credentials if you ever forget them
        </pre>

        <p>But if you're locked out of your discord account, just click the 'Reset' button. It will do the same
        thing as <strong>/lynxreset</strong></p>

        <div id="verify-parent">
            <button id="verify-btn" onclick="reset()">Reset</button>
        </div>
        """,
        "script": """
            async function reset() {
                document.querySelector("#verify-btn").innerText = "Resetting...";

                ws.send(JSON.stringify({request: "reset"}))
            }
        """
    })

@app.post("/reset-creds")
async def reset_creds(request: Request):
    # Remove from db
    await app.state.db.execute(
        "UPDATE users SET api_token = $1, staff_verify_code = NULL WHERE user_id = $2",
        get_token(132),
        int(request.scope["sunbeam_user"]["user"]["id"])
    )
    return ORJSONResponse({"detail": "Done"})

def bot_select(id: str, bot_list: list[str], reason: bool = False):
    select = f"""
<label for='{id}'>Choose a bot</label><br/>
<select name='{id}' id='{id}'> 
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
<input type="number" id="{id}-alt" name="{id}-alt" />
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

app.state.valid_csrf = {}
app.state.valid_csrf_user = {}

@app.get("/bot-actions")
async def loa(request: Request, response: Response):
    queue = await app.state.db.fetch("SELECT bot_id, username_cached, description, prefix, created_at FROM bots WHERE state = $1 ORDER BY created_at ASC", enums.BotState.pending)

    queue_select = bot_select("queue", queue)

    under_review = await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.under_review)

    under_review_select_approved = bot_select("under_review_approved", under_review, reason=True)
    under_review_select_denied = bot_select("under_review_denied", under_review, reason=True)
    under_review_select_claim = bot_select("under_review_claim", under_review, reason=True)
    
    approved = await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1 ORDER BY created_at DESC", enums.BotState.approved)

    ban_select = bot_select("ban", approved, reason=True)
    certify_select = bot_select("certify", approved, reason=True)
    unban_select = bot_select("unban", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.banned), reason=True)
    unverify_select = bot_select("unverify", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.approved), reason=True)
    requeue_select = bot_select("requeue", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1 OR state = $2", enums.BotState.denied, enums.BotState.banned), reason=True)

    uncertify_select = bot_select("uncertify", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1", enums.BotState.certified), reason=True)

    reset_bot_votes_select = bot_select("reset-votes", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots WHERE state = $1 OR state = $2", enums.BotState.approved, enums.BotState.certified), reason=True)

    flag_list = list(enums.BotFlag)
    flags_select = "<label>Select Flag</label><select id='flag' name='flag'>"
    for flag in flag_list:
        flags_select += f"<option value={flag.value}>{flag.name} ({flag.value}) -> {flag.__doc__}</option>"
    flags_select += "</select>"

    flags_bot_select = bot_select("set-flag", await app.state.db.fetch("SELECT bot_id, username_cached FROM bots"), reason=True)

    # Easiest way to block cross origin is to just use a hidden input
    csrf_token = get_token(132)
    app.state.valid_csrf |= {csrf_token: time.time()}

    response.set_cookie("csrf_token_ba", csrf_token, max_age=60*10, domain="lynx.fateslist.xyz", path="/bot-actions", secure=True, httponly=True, samesite="Strict")

    queue_md = ""

    for bot in queue:
        owners = await app.state.db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot["bot_id"])
        
        owners_md = ""

        for owner in owners:
            user = await fetch_user(owner["owner"])
            owners_md += f"""
{user['username']}  ({owner['owner']}) |  main -> {owner["main"]}
            """
        
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
        .use(container_plugin, name="generic", validate = lambda *args: True)
        .enable('table')
        .enable('image')
    )

    return {
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
    "ext_script": "/_static/bot-actions.js",
    "script": f"""
        var csrfToken = "{csrf_token}"
    """}

class Action(BaseModel):
    bot_id: str
    owners: list[dict] | None = None # This is filled in by action decorator
    main_owner: int | None = None # This is filled in by action decorator
    context: Any | None = None

class ActionWithReason(Action):
    reason: str

def action(
    states: list[enums.BotState], 
    with_reason: bool, 
    min_perm: int = 2,
    action_log: enums.UserBotAction | None = None
):
    async def state_check(bot_id: int):
        bot_state = await app.state.db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        return (bot_state in states) or len(states) == 0
    
    async def _core(request: Request, csrf_token: str, data: Action):
        if request.state.member.perm < min_perm:
            return ORJSONResponse({
                "detail": f"This operation has a minimum perm of {min_perm} but you have permission level {request.state.member.perm}"
            }, status_code=400)

        if csrf_token != request.cookies.get("csrf_token_ba") or csrf_token not in app.state.valid_csrf:
            return ORJSONResponse({
                "detail": "CSRF Token is invalid. Consider copy pasting reason and reloading your page"
            }, status_code=400)
        if not data.bot_id.isdigit():
            return ORJSONResponse({
                "detail": "Bot ID is invalid"
            }, status_code=400)
        data.bot_id = int(data.bot_id)
        
        if not await state_check(data.bot_id):
            return ORJSONResponse({
                "detail": f"Bot is not in acceptable states or doesn't exist: Acceptable states are {states}"
            }, status_code=400)
        
        data.owners = await app.state.db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", data.bot_id)

        for owner in data.owners:
            if owner["main"]:
                data.main_owner = owner["owner"]
                break

    def decorator(function):
        if not with_reason:
            async def wrapper(request: Request, csrf_token: str, data: Action):
                if res := await _core(request, csrf_token, data):
                    return res
                res = await function(request, data)
                if action_log:
                    ... 
                return res
        else:
            async def wrapper(request: Request, csrf_token: str, data: ActionWithReason):
                if res := await _core(request, csrf_token, data):
                    return res
                if len(data.reason) < 5:
                    return ORJSONResponse({
                        "detail": "Reason must be more than 5 characters"
                    }, status_code=400)
                res = await function(request, data)
                if action_log:
                    ...
                return res
        return wrapper
    return decorator

# TODO: Implement this if we go ahead with this
@app.post("/bot-actions/claim")
@action([enums.BotState.pending], with_reason=False)
async def claim(request: Request, data: Action):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.under_review, request.state.user_id, int(data.bot_id))
    
    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Claimed",
        description=f"<@{request.state.user_id}> has claimed <@{data.bot_id}> and this bot is now under review.\n**If all goes well, this bot should be approved (or denied) soon!**\n\nThank you for using Fates List :heart:",
    )

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})
    return {"detail": "Successfully claimed bot!"}

@app.post("/bot-actions/unclaim")
@action([enums.BotState.under_review], with_reason=True)
async def unclaim(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Unclaimed",
        description=f"<@{request.state.user_id}> has stopped testing <@{data.bot_id}> for now and this bot is now pending review from another bot reviewer.\n**This is perfectly normal. All bot reviewers need breaks too! If all goes well, this bot should be approved (or denied) soon!**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully unclaimed bot"}

@app.post("/bot-actions/approve")
@action([enums.BotState.under_review], with_reason=True)
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

    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2, guild_count = $3 WHERE bot_id = $4", enums.BotState.approved, request.state.user_id, approx_guild_count, data.bot_id)
    
    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Approved!",
        description=f"<@{request.state.user_id}> has approved <@{data.bot_id}>\nCongratulations on your accompishment and thank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)
    embed.add_field(name="Guild Count (approx)", value=str(approx_guild_count))

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})
    
    for owner in data.owners:
        asyncio.create_task(add_role(main_server, owner["owner"], bot_developer, "Bot Approved"))

    return {"detail": "Successfully approved bot", "guild_id": str(main_server)}

@app.post("/bot-actions/deny")
@action([enums.BotState.under_review], with_reason=True)
async def deny(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.denied, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0xe74c3c,
        title="Bot Denied",
        description=f"<@{request.state.user_id}> has denied <@{data.bot_id}>!\n**Once you've fixed what we've asked you to fix, please resubmit your bot by going to `Bot Settings`.**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully denied bot"}

@app.post("/bot-actions/ban")
@action([enums.BotState.approved], min_perm=4, with_reason=True)
async def ban(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.banned, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0xe74c3c,
        title="Bot Banned",
        description=f"<@{request.state.user_id}> has banned <@{data.bot_id}>!\n**Once you've fixed what we've need you to fix, please appeal your ban by going to `Bot Settings`.**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    asyncio.create_task(ban_user(main_server, data.bot_id, data.reason))

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully banned bot"}

@app.post("/bot-actions/unban")
@action([enums.BotState.banned], min_perm=4, with_reason=True)
async def unban(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.approved, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Unbanned",
        description=f"<@{request.state.user_id}> has unbanned <@{data.bot_id}>!\n\nThank you for using Fates List again and sorry for any inconveniences caused! :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    asyncio.create_task(unban_user(main_server, data.bot_id, data.reason))

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully unbanned bot"}

@app.post("/bot-actions/certify")
@action([enums.BotState.approved], with_reason=True, min_perm=5)
async def certify(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.certified, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Certified",
        description=f"<@{request.state.user_id}> has certified <@{data.bot_id}>.\n**Good Job!!!**\n\nThank you for using Fates List :heart:",
    )

    embed.add_field(name="Feedback", value=data.reason)

    for owner in data.owners:
        asyncio.create_task(add_role(main_server, owner["owner"], certified_developer, "Bot certified - owner gets role"))

    # Add certified bot role to bot
    asyncio.create_task(add_role(main_server, data.bot_id, certified_bot, "Bot certified - add bots role"))

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully certified bot"}

@app.post("/bot-actions/uncertify")
@action([enums.BotState.certified], with_reason=True, min_perm=5)
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
        asyncio.create_task(del_role(main_server, owner["owner"], certified_developer, "Bot uncertified - Owner gets role"))

    # Add certified bot role to bot
    asyncio.create_task(del_role(main_server, data.bot_id, certified_bot, "Bot uncertified - Bots Role"))

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully uncertified bot"}

@app.post("/bot-actions/unverify")
@action([enums.BotState.approved], with_reason=True, min_perm=3)
async def unverify(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.pending, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0xe74c3c,
        title="Bot Unverified",
        description=f"<@{request.state.user_id}> has unverified <@{data.bot_id}> due to some issues we are looking into!\n\nThank you for using Fates List and we thank you for your patience :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully unverified bot"}

@app.post("/bot-actions/requeue")
@action([enums.BotState.banned, enums.BotState.denied], with_reason=True, min_perm=3)
async def requeue(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.pending, request.state.user_id, data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0x00ff00,
        title="Bot Requeued",
        description=f"<@{request.state.user_id}> has requeued <@{data.bot_id}> for re-review!\n\nThank you for using Fates List and we thank you for your patience :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully requeued bot"}

@app.post("/bot-actions/reset-votes")
@action([], with_reason=True, min_perm=3)
async def reset_votes(request: Request, data: ActionWithReason):
    await app.state.db.execute("UPDATE bots SET votes = 0 WHERE bot_id = $1", data.bot_id)

    embed = Embed(
        url=f"https://fateslist.xyz/bot/{data.bot_id}", 
        color=0xe74c3c,
        title="Bot Votes Reset",
        description=f"<@{request.state.user_id}> has force resetted <@{data.bot_id}> votes due to abuse!\n\nThank you for using Fates List and we are sorry for any inconveniences caused :heart:",
    )

    embed.add_field(name="Reason", value=data.reason)

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully reset bot votes"}

@app.post("/bot-actions/set-flag")
@action([], with_reason=True, min_perm=3)
async def set_flags(request: Request, data: ActionWithReason):
    if not isinstance(data.context, int):
        return ORJSONResponse({"detail": "Flag must be an integer"}, status_code=400)
    try:
        flag = enums.BotFlag(data.context)
    except:
        return ORJSONResponse({"detail": "Flag must be of enum Flag"}, status_code=400)
    
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

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully set flag"}

@app.post("/bot-actions/unset-flag")
@action([], with_reason=True, min_perm=3)
async def unset_flags(request: Request, data: ActionWithReason):
    if not isinstance(data.context, int):
        return ORJSONResponse({"detail": "Flag must be an integer"}, status_code=400)
    try:
        flag = enums.BotFlag(data.context)
    except:
        return ORJSONResponse({"detail": "Flag must be of enum Flag"}, status_code=400)
    
    existing_flags = await app.state.db.fetchval("SELECT flags FROM bots WHERE bot_id = $1", data.bot_id)
    existing_flags = existing_flags or []
    existing_flags = set(existing_flags)
    try:
        existing_flags.remove(int(flag))
    except:
        return ORJSONResponse({"detail": "Flag not on this bot"}, status_code=400)

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

    await redis_ipc_new(app.state.redis, "SENDMSG", msg={"content": f"<@{data.main_owner}>", "embed": embed.to_dict(), "channel_id": str(bot_logs)})

    return {"detail": "Successfully unset flag"}

@app.get("/requests")
async def lynx_request_logs():
    requests = await app.state.db.fetch("SELECT user_id, method, url, status_code, request_time from lynx_logs")
    requests_html = ""
    for request in requests:
        requests_html += f"""
        <p>{request["user_id"]} - {request["method"]} - {request["url"]} - {request["status_code"]} - {request["request_time"]}</p>
        """

    return ORJSONResponse({
        "title": "Lynx Request Logs",
        "pre": "/links",
        "data": f"""
        {requests_html}
        """
    })        

@app.post("/verify-code")
async def verify_code(request: Request):
    if request.state.is_verified:
        return ORJSONResponse({
            "detail": "You are already verified"
        },
        status_code=400
        )
    try:
        body = await request.json()
        code = body["code"]
    except:
        return ORJSONResponse({"detail": "Bad Request"}, status_code=400)

    if not code_check(body["code"], int(request.scope["sunbeam_user"]["user"]["id"])):
        return ORJSONResponse({"detail": "Invalid code"}, status_code=400)
    else:
        username = request.scope["sunbeam_user"]["user"]["username"]
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
            return ORJSONResponse({"detail": "Failed to create user on lynx"}, status_code=500)

        await app.state.db.execute(
            "UPDATE users SET staff_verify_code = $1 WHERE user_id = $2", 
            body["code"],
            int(request.scope["sunbeam_user"]["user"]["id"]),
        )

        await add_role(staff_server, request.scope["sunbeam_user"]["user"]["id"], access_granted_role, "Access granted to server")
        await add_role(staff_server, request.scope["sunbeam_user"]["user"]["id"], request.state.member.staff_id, "Gets corresponding staff role")
        
        return ORJSONResponse({"detail": "Successfully verified staff member", "pass": password})

@app.get("/_new_html")
def new_html(request: Request):
    if request.headers.get("CF-Connecting-IP"):
        print("Ignoring malicious new html request")
        return
    with open("modules/infra/admin_piccolo/lynx-ui.html") as f:
        app.state.lynx_form_beta = f.read()
    
    return

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
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_notifs(self, ws: WebSocket):
        notifs = await app.state.db.fetch("SELECT id, acked_users, message, type, staff_only FROM lynx_notifications")
        _send_notifs = []
        for notif in notifs:
            if notif["staff_only"]:
                if ws.state.member.perm >= 2:
                    _send_notifs.append(notif)
                    
            else:
                _send_notifs.append(notif)
        await self.send_personal_message({"resp": "notifs", "data": jsonable_encoder(_send_notifs)}, ws)

    async def send_doctree(self, ws: WebSocket):
        await self.send_personal_message({"resp": "doctree", "data": doctree_gen().replace("\n", "")}, ws)

    async def send_docs(self, ws: WebSocket, page: str, source: bool):
        if page.endswith(".md"):
            page = f"/docs/{page[:-3]}"
        
        elif not page or page == "/docs":
            page = "/index"

        if not page.replace("-", "").replace("_", "").replace("/", "").isalnum():
            return await self.send_personal_message({"resp": "docs", "detail": "Invalid page"}, ws)
        
        try:
            with open(f"modules/infra/admin_piccolo/api-docs/{page}.md", "r") as f:
                md_data = f.read()
        except FileNotFoundError as exc:
            return await self.send_personal_message({"resp": "docs", "detail": f"api-docs/{page}.md not found -> {exc}"}, ws)

        # Inject rating code
        md_data = f"""
### Feedback

Just want to provide feedback? [Rate this page](#rate-this-page)

{md_data}

### Rate this page!

- Your feedback allows Fates List to improve our docs. 
- We would also *love* it you could make a Pull Request at [https://github.com/Fates-List/infra](https://github.com/Fates-List/infra)
- Starring the repo is also a great way to show your support!

<label for='doc-feedback'>Your Feedback</label>
<textarea 
id='doc-feedback'
name='doc-feedback'
placeholder='I feel like you could...'
></textarea>

<button onclick='rateDoc()'>Rate</button>

### [View Source](https://lynx.fateslist.xyz/docs-src/{page})
        """

        # If looking for source
        if source:
            print("Sending source")
            return await self.send_personal_message({
                "resp": "docs",
                "title": page.split('/')[-1].replace('-', ' ').title() + " (Source)",
                "data": f"""
        <pre>{md_data.replace('<', '&lt').replace('>', '&gt')}</pre>
                """
            }, ws)

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
            .use(container_plugin, name="generic", validate = lambda *args: True)
            .enable('table')
            .enable('image')
        )

        return await self.send_personal_message({
            "resp": "docs",
            "title": page.split('/')[-1].replace('-', ' ').title(),
            "data": md.render(md_data).replace("<table", "<table class='table'").replace(".md", ""),
            "ext_script": "/_static/docs.js?v=6",
        }, ws)
    
    async def send_loa(self, ws: WebSocket):
        if ws.state.member.perm < 2:
            return await self.send_personal_message({"resp": "loa", "detail": "You do not have permission to view this page", "wait_for_upg": True}, ws)
        return await self.send_personal_message({
            "resp": "loa",
            "title": "Leave Of Absense",
            "pre": "/links",
            "data": f"""
Just a tip for those new to lynx (for now)
<ol>
    <li>Login to Lynx Admin</li>
    <li>Click Leave Of Absense</li>
    <li>Click 'Add Row'</li>
    <li>Fill out the nessesary fields</li>
    <li>Click 'Save'</li>
</ol>
<strong>A way to actually create LOA's from this page is coming soon :)</strong>
            """
        }, ws)

    async def send_links(self, ws: WebSocket):
        if ws.state.member.perm > 2:
            return await self.send_personal_message({
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
            """}, ws)
        else:
            return await self.send_personal_message({
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
            """}, ws)

manager = ConnectionManager()


@app.websocket("/_ws")
async def ws(ws: WebSocket):
    if ws.headers.get("Origin") != "https://lynx.fateslist.xyz":
        print(f"Ignoring malicious websocket request with origin {ws.headers.get('Origin')}")
        return

    ws.state.user = None
    ws.state.member = StaffMember(name="Unknown", id=0, perm=1, staff_id=0)

    await manager.connect(ws)

    await manager.send_personal_message({"detail": "connected"}, ws)

    try:
        while True:
            data = await ws.receive_json()

            if data.get("request") == "notifs":
                asyncio.create_task(manager.send_notifs(ws))
            elif data.get("request") == "doctree":
                asyncio.create_task(manager.send_doctree(ws))
            elif data.get("request") == "perms": 
                await manager.send_personal_message({"resp": "perms", "data": ws.state.member.dict()}, ws)
            elif data.get("request") == "reset":
                # Remove from db
                if ws.state.user:
                    await app.state.db.execute(
                        "UPDATE users SET api_token = $1, staff_verify_code = NULL WHERE user_id = $2",
                        get_token(132),
                        int(ws.state.user["id"])
                    )
                    await manager.send_personal_message({"resp": "reset", "data": None}, ws)
            elif data.get("request") == "upgrade":
                sunbeam_user = data.get("data", {})
                if sunbeam_user.get("user"):
                    if not sunbeam_user["user"].get("id", "").isdigit() or not sunbeam_user.get("token"):
                        await ws.close(code=1009, message="Invalid ws init")
                        return
                    check = await app.state.db.fetchval(
                        "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", 
                        int(sunbeam_user["user"]["id"]), 
                        sunbeam_user["token"]
                    )
                    if not check:
                        await ws.close(code=1008, message="Invalid token")
                        return
                    ws.state.user = sunbeam_user["user"]

                    _, _, member = await is_staff(None, int(sunbeam_user["user"]["id"]), 2, redis=app.state.redis)

                    ws.state.member = member
                
                # Send new perms on upgrade
                await manager.send_personal_message({"resp": "perms", "data": ws.state.member.dict()}, ws)
            elif data.get("request") == "docs":
                # Get the doc path
                print(data)
                path = data.get("path", "/").split("#")[0]
                source = data.get("source", False)
                asyncio.create_task(manager.send_docs(ws, path, source))
            elif data.get("request") == "links":
                asyncio.create_task(manager.send_links(ws))
            elif data.get("request") == "staff_guide":
                await manager.send_personal_message({"resp": "staff_guide", "title": "Staff Guide", "data": staff_guide}, ws)
            elif data.get("request") == "index":
                await manager.send_personal_message({"resp": "staff_guide", "title": "Welcome To Lynx", "data": """
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
                """}, ws)
            elif data.get("request") == "loa":
                asyncio.create_task(manager.send_loa(ws))

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast(orjson.dumps({"detail": "Client left the chat"}).decode())

class Rating(BaseModel):
    feedback: str
    page: str

@app.get("/_user")
async def user_ws_get(request: Request):
    if not request.headers.get("Frostpaw-Websocket-Conn"):
        return {}
    return request.scope.get("sunbeam_user", {})

@app.post("/_eternatus")
async def eternatus_rating(request: Request, rating: Rating):
    if len(rating.feedback) < 5:
        return ORJSONResponse({"detail": "Feedback must be greater than 10 characters long!"}, status_code=400)
    
    if request.scope.get("sunbeam_user"):
        user_id = int(request.scope["sunbeam_user"]["user"]["id"])
        username = request.scope["sunbeam_user"]["user"]["username"]
    else:
        user_id = None
        username = "Anonymous"

    if not rating.page.startswith("/"):
        return ORJSONResponse({"detail": "Unexpected page!"}, status_code=400)
    
    await app.state.db.execute(
        "INSERT INTO lynx_ratings (feedback, page, username_cached, user_id) VALUES ($1, $2, $3, $4)",
        rating.feedback,
        rating.page,
        username,
        user_id
    )
    
    return {"detail": "Successfully rated"}

@app.get("/user-actions")
async def user_actions(request: Request, response: Response, id: int | None = None):
    # Easiest way to block cross origin is to just use a hidden input
    csrf_token = get_token(132)
    app.state.valid_csrf_user |= {csrf_token: time.time()}

    response.set_cookie("csrf_token_ua", csrf_token, max_age=60*10, domain="lynx.fateslist.xyz", path="/user-actions", secure=True, httponly=True, samesite="Strict")

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
        .use(container_plugin, name="generic", validate = lambda *args: True)
        .enable('table')
        .enable('image')
    )

    return {
        "title": "User Actions",
        "data": md.render(f"""
            
<div class="panel panel-default">
  <div class="panel-heading">
    <h3 class="panel-title">Add Staff</h3>
  </div>
  <div class="panel-body">
    - Head Admin+ only
<div class="form-group">
<label for="staff_user_id">User ID</label>
<input class="form-control" id="staff_user_id" name="staff_user_id" placeholder='user id here' type="number" value="{id or ''}" />
<button class="btn btn-primary" onclick="addStaff()">Add</button>
</div>
  </div>
</div>
        """),
        "script": f"""
        var csrfToken = "{csrf_token}"
        """ + """
            async function addStaff() {
                let userId = document.querySelector("#staff_user_id").value
                let res = await fetch(`/user-actions/addstaff?csrf_token=${csrfToken}`, {
                    method: "POST",
                    credentials: 'same-origin',
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({"user_id": userId}),
                })
                let json = await res.json()
                alert(json.detail)
            }
        """
    }

class UserAction(BaseModel):
    user_id: str

class UserActionWithReason(UserAction):
    reason: str

def user_action(
    states: list[enums.UserState], 
    with_reason: bool, 
    min_perm: int = 2,
):
    async def state_check(bot_id: int):
        user_state = await app.state.db.fetchval("SELECT state FROM users WHERE user_id = $1", bot_id)
        return (user_state in states) or len(states) == 0
    
    async def _core(request: Request, csrf_token: str, data: UserAction):
        if request.state.member.perm < min_perm:
            return ORJSONResponse({
                "detail": f"This operation has a minimum perm of {min_perm} but you have permission level {request.state.member.perm}"
            }, status_code=400)

        if csrf_token != request.cookies.get("csrf_token_ua") or csrf_token not in app.state.valid_csrf_user:
            return ORJSONResponse({
                "detail": "CSRF Token is invalid. Consider copy pasting reason and reloading your page"
            }, status_code=400)
        if not data.user_id.isdigit():
            return ORJSONResponse({
                "detail": "User ID is invalid"
            }, status_code=400)
        data.user_id = int(data.user_id)
        
        if not await state_check(data.user_id):
            return ORJSONResponse({
                "detail": f"User is not in acceptable states or doesn't exist: Acceptable states are {states}"
            }, status_code=400)
        
    def decorator(function):
        if not with_reason:
            async def wrapper(request: Request, csrf_token: str, data: UserAction):
                if res := await _core(request, csrf_token, data):
                    return res
                res = await function(request, data)
                return res
        else:
            async def wrapper(request: Request, csrf_token: str, data: UserActionWithReason):
                if res := await _core(request, csrf_token, data):
                    return res
                if len(data.reason) < 5:
                    return ORJSONResponse({
                        "detail": "Reason must be more than 5 characters"
                    }, status_code=400)
                res = await function(request, data)
                return res
        return wrapper
    return decorator


@app.post("/user-actions/addstaff")
@user_action([enums.UserState.normal], with_reason=False, min_perm=5)
async def addstaff(request: Request, data: UserAction):
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
                return ORJSONResponse({
                    "detail": f"User is not DMable {json}"
                }, status_code=400)
            json = await res.json()
            channel_id = json["id"]

        embed = Embed(
            color=0xe74c3c,
            title="Staff Application Accepted",
            description=f"You have been accepted into the Fates List Staff Team!",
        )

        async with sess.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            json={
                "content": """
Please join our staff server first of all: https://fateslist.xyz/banappeal/invite

Then head on over to https://lynx.fateslist.xyz to read our staff guide and get started!
                """, 
                "embeds": [embed.to_dict()],
            },
            headers={"Authorization": f"Bot {main_bot_token}"}
        ) as resp:
            if resp.status != 200:
                json = await resp.json()
                return ORJSONResponse({
                    "detail": f"Failed to send DM to user {json}"
                }, status_code=400)

    return {"detail": "Successfully added staff member"}

@app.post("/user-actions/staff-apps/ack")
@user_action([], with_reason=False, min_perm=4)
async def delete_staff_apps_by_id(request: Request, data: UserAction):
    await app.state.db.execute("DELETE FROM lynx_apps WHERE user_id = $1", data.user_id)

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

app.add_middleware(CustomHeaderMiddleware)
