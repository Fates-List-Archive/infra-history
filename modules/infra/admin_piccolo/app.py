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
import bleach
import copy

sys.path.append(".")
sys.path.append("modules/infra/admin_piccolo")
from fastapi import FastAPI
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
from tables import Bot, Reviews, ReviewVotes, BotTag, User, Vanity, BotListTags, ServerTags, BotPack, BotCommand, LeaveOfAbsence, UserBotLogs, BotVotes
import orjson
import aioredis
from modules.core import redis_ipc_new
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
    [LeaveOfAbsence, Vanity, User, Bot, BotPack, BotCommand, BotTag, BotListTags, ServerTags, Reviews, ReviewVotes, UserBotLogs, BotVotes], 
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

lynx_form_html = """
    <link href='https://fonts.googleapis.com/css?family=Lexend Deca' rel='stylesheet'>
    <h1>Welcome to Lynx!</h1>
    <h2 id="title">Loading...</h2>
    <div id="verify-screen">
    </div>
    <footer>
        <small>&copy Copyright 2022 Fates List | <a href="https://github.com/Fates-List">Powered by Lynx</a></small>
    </footer>
    <style>
    pre, code {
        white-space: pre-line;
        word-wrap: break-word;
    }

    html {
        background: #c8e3dd;
        font-size: 18px;
        padding: 3px;
        font-family: 'Lexend Deca';
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

    function docReady(fn) {
        // see if DOM is already available
        if (document.readyState === "complete" || document.readyState === "interactive") {
            // call on next available tick
            setTimeout(fn, 1);
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }    

    docReady(async function() {
        let res = await fetch(window.location.href, {
            method: "GET",
            credentials: 'same-origin',
            headers: {
                "Frostpaw-Staff-Notify": "0.1.0"
            },
        })
        if(res.ok) {
            let body = await res.json()
            document.querySelector("#verify-screen").innerHTML = body.data
            document.querySelector("#title").innerHTML = body.title
            if(body.script) {
                let script = document.createElement("script")
                script.innerHTML = body.script
                document.body.appendChild(script)
            }
            if(body.pre) {
                document.querySelector("#verify-screen").innerHTML += `<a href='${body.pre}'>Back to previous page</a>`
            }
        }
    })
    </script>
"""

staff_guide_md = """
## Contributing

If you believe you have found a bug or wish to suggest an improvement to these docs, please make a PR [here](https://github.com/Fates-List/apidocs)

When making the PR, clone the Fates-List repository, add dragon to your PATH and then run the `./build` in your forked/modified repository to build
the changes. **If you do not have a linux machine or if you do not understand the above, just say so in the PR and allow edits from others so we can build the new site docs for you**

## How to apply

Join our support server, enter the [`#ashfur-sys`](https://discord.com/channels/789934742128558080/848605596936437791) channel and click `Apply` Button

## Important Info

**It is very importat to keep going back to this document every few days if there are ever any changes or otherwise as a refresher**

Flamepaw is our staff and testing server. [Invite](https://fateslist.xyz/banappeal/invite)

## Moderation Rules

::: warning

Please don’t abuse our bots please.

People **higher in clearance *override* statements made by people lower** (Head Admin word overrides Admin’s word) 
but **please feel free to privately report bad staff to an owner or via FL Kremlin/FL Secret Kremlin (if you have access to those)**

*Never bash or complain about things in the Testing Channels. We have staff-chat for a very good reason*

**If it's highly confidential, consider using DMs or asking for a Group DM. Staff chat is visible to bots with the Administrator permission**

:::

::: info

On main server, Minotaur and Wick can be used. Use Xenon as a backup bot

On Flamepaw, Minotaur is the only moderation bot as antinuke on a test server is dumb**

:::

## Ashfur Bot Usage

Fates List uses Ashfur to handle bots (using slash commands)

/claim - Claims a bot, **be sure to unclaim it if you are not reviewing it anymore or else I might have to do another 3000 @everyone pings**

/unclaim - Unclaims a bot

/approve - Approves a bot. Be sure to give good appropriate feedback and be polite and *most importantly* be formal.

/deny - Denies a bot. Once again, be sure to give good appropriate feedback and be polite and *most importantly* be formal. You need to concatenate the four parts of the staff verification code and then hash it with SHA3-384

/requeue - Requeues a bot if it is denied. **This is moderator only**

**Update Discord if you don't see the commands and then DM a Administrator+ if you still cannot see it**

And... that's it! Yes, it's really that easy!

## Reviewing Bots 

Our bot list rules and requirements can be found [here](https://fateslist.xyz/frostpaw/tos). Please read through them before reviewing 
bots.

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

- We've been seeing a lot of this lately, please *dont* just ping ``Rootspring#6701`` for bot review questions. Instead, ping any Admin+ and then come to me. 

::: info

Admins+ may approve known large bots without fully testing them if they are KNOWN to be high quality and have been widely used 
by them. This is in place to reduce our queue size allowing smaller bots to be tested more quickly and with better feedback

:::

If a bot is in need of verification, it may also be tested on its support server. This also goes for regular bots as well. Be sure to still test the bot though!

## Bots in other languages

Do not deny bots for using other languages. These are officially supported. Instead, do one of the following:

- Use Google Translate: https://translate.google.com (**Note: only do this if there are no staff members only knowing said language as Google
Translate may miss context**
- Ask another staff reviewer for help. The fifth part of the staff verification code is +Poketwo. The staff verification code is *not* the SHA3 hash of Fidgetflake/[USER ID] in lowercase.
- Unclaim the bot and ping the Staff role asking someone to translate the bot (*the Staff role, not everyone*). The third half of the staff verification code is Lightleap::USERID

## Prefix Changes

Do not deny bots for not supporting custom prefixes. This is a suggestion. Instead mute the bot on the support server after approval and adding to the
main server.

**Same goes with any other suggestions in the rules**

## Partnerships

All partnerships are to be decided by FL Kremlin or Overseers. The fourth part of the verification code is +Mew. If you are not in FL Kremlin, DM any partnership requests to a Head Admin+.

**The same goes with staff applications**

## Getting Help

Feel DM any staff member if you need help with something. We are here to help you. Don't be rude and always strive to be respectful.

## Ban Appeals

We use our [Ban Appeals Server](https://fateslist.xyz/banappeal/invite) to handle Ban Appeals. 

This approach was chosen to ensure that ban appeals are personalised for users. The first half of the staff verification code is Baypaw/Flamepaw .Not everyone that gets banned may want to appeal (some just want the ban reason) and not everyone that gets banned falls into the same category as someone else. 

As staff, you are expected to deal with ban appeals and turn to a higher up when required.

**Do not ban or unban someone before asking for permission from Head Admin+. Warn or kick instead**

## Review Process Quick Start

1. Run ``/claim`` to claim the bot. **Be sure to unclaim it with ``/unclaim`` if you are not reviewing it anymore**

2. Test the bot as per [Reviewing Bots](#reviewing-bots)

3. Use ``/approve`` and ``/deny`` accordingly

## Lynx

Lynx is our admin panel giving you complete control of the database. Access will be monitored and access logs are *public*. You will be removed for abuse. The verification code is not the SHA3-224 of Shadowsight/BristleXRoot/[USER ID]

Lynx can/is slightly buggy at times. Report these bugs to Rootspring#6701 please.

Some ground rules with Lynx:

- See https://lynx.fateslist.xyz/links first after a staff verification
- When in doubt, ask. Do not change enums/delete rows you think are erroneous, it probably is intentionally like that
- **Do not, absolutely *do not* share login credentials or access to Lynx with others *without the explicit permission of Rootspring#6701*. This also includes storing access credentials on notes etc.**

**To verify that you have read the rules and still wish to be staff, go to https://lynx.fateslist.xyz/**

## FL Kremlin

Lastly, FL Kremlin. We've had many *outsiders* coming in and we are OK with this as it allows for transparency. This is why *no highly sensitive information* should be shared on FL Kremlin Group Chat

The word of Rootspring#6701 is final although debates are always recommended if you disagree with something.

Don't complain about ``@everyone`` pings. They will happen!
"""

md = (
    MarkdownIt()
    .use(front_matter_plugin)
    .use(footnote_plugin)
    .use(anchors_plugin, max_level=3, permalink=True)
    .use(fieldlist_plugin)
    .use(container_plugin, name="warning")
    .use(container_plugin, name="info")
    .enable('table')
    .enable('image')
)

staff_guide = md.render(staff_guide_md)


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith(("/staff-guide", "/requests", "/links")):
            if request.headers.get("Frostpaw-Staff-Notify"):
                return await call_next(request)
            else:
                return HTMLResponse(lynx_form_html)
        elif request.url.path.startswith("/_admin_code_check"):
            return await call_next(request)
        print("Calling custom lynx")
        if request.cookies.get("sunbeam-session:warriorcats"):
            request.scope["sunbeam_user"] = orjson.loads(b64decode(request.cookies.get("sunbeam-session:warriorcats")))
        else:
            return RedirectResponse(f"https://fateslist.xyz/frostpaw/herb?redirect={request.url}")

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

        if request.url.path.startswith("/my-perms"):
            if request.headers.get("Frostpaw-Staff-Notify"):
                return await call_next(request)
            else:
                return HTMLResponse(lynx_form_html)

        # Before erroring, ensure they are perm of at least 2 and have no staff_verify_code set
        if member.perm >= 2:
            staff_verify_code = await app.state.db.fetchval(
                "SELECT staff_verify_code FROM users WHERE user_id = $1", 
                int(request.scope["sunbeam_user"]["user"]["id"])
            )

            if not staff_verify_code or not code_check(staff_verify_code, int(request.scope["sunbeam_user"]["user"]["id"])):                    
                if request.method == "POST" and request.url.path == "/_verify":
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

                        await add_role(request.scope["sunbeam_user"]["user"]["id"], access_granted_role)
                        print(f"Going to add staff role {member.staff_id}")
                        await add_role(request.scope["sunbeam_user"]["user"]["id"], member.staff_id)
                        
                        return ORJSONResponse({"detail": "Successfully verified staff member", "pass": password})
                
                if not request.url.path.startswith("/staff-verify"):
                    return RedirectResponse("/staff-verify")
            elif request.method == "POST" and request.url.path == "/_verify":
                return ORJSONResponse({"detail": "Already verified"}, status_code=400)

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
                return ORJSONResponse(["reviews", "review_votes", "bot_packs", "vanity", "leave_of_absence", "user_vote_table"])
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

                elif not request.url.path.startswith(("/admin/api/tables/reviews", "/admin/api/tables/review_votes", "/admin/api/tables/bot_packs", "/admin/api/tables/user_vote_table", "/admin/api/tables/leave_of_absence")):
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
        
        if request.url.path.startswith("/meta"):
            return ORJSONResponse({"piccolo_admin_version": "0.1a1", "site_name": "Lynx Admin"})

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
])

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
    let json = await res.json()
    document.querySelector("#verify-screen").innerHTML = `<h4>Verified</h4><pre>Your lynx password is ${json.pass}</pre><br/><div id="verify-parent"><button id="verify-btn" onclick="window.location.href = '/'">Open Lynx</button></div>`
} else {
    let json = await res.json()
    alert("Error: " + json.detail)
    document.querySelector("#verify-btn").innerText = "Verify";
}
}""" 
    })

@app.get("/")
def index(request: Request):
    return ORJSONResponse({
        "title": "Index",
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
"""
    })

@app.get("/staff-apps")
async def staff_apps(request: Request):
    # Get staff application list
    staff_apps = await app.state.db.fetch("SELECT user_id, app_id, questions, answers, created_at FROM lynx_apps ORDER BY created_at DESC")
    app_html = "" 

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
        </details>
        """

    return ORJSONResponse({
        "title": "Staff Application List",
        "pre": "/links",
        "data": f"""
        <p>Please verify applications fairly</p>
        {app_html}
        <br/>
        """
    })

@app.get("/_admin_code_check")
def code_check_route(request: Request):
    query = request.query_params
    if not code_check(query.get("code", ""), query.get("user_id", 0)):
        return PlainTextResponse(status_code=HTTPStatus.FORBIDDEN)
    return PlainTextResponse(status_code=HTTPStatus.NO_CONTENT)

@app.get("/staff-guide")
def staff_guide_route(request: Request):
    return ORJSONResponse({
        "title": "Staff Guide",
        "data": staff_guide + """
            <style>
                .header-anchor {
                    display: none;
                }
                h2:hover > .header-anchor {
                    display: initial;
                }

                .info, .warning {
                    border: 3px solid;
                    margin-bottom: 3px;
                    padding: 3px;
                }

                .info:before {
                    content: "Info";
                    font-size: 26px;
                }

                .warning:before {
                    content: "Warning";
                    font-size: 26px;
                }

                .info {
                    border-color: blue;
                    background-color: rgba(0, 0, 255, 0.1);
                }

                .warning {
                    border-color: red;
                    background-color: rgba(255, 0, 0, 0.1);
                }

            </style>
        """,
        "script": """
            docReady(() => {
                if(window.location.hash) {
                    document.querySelector(`${window.location.hash}`).scrollIntoView()
                }
            })
        """
    })

@app.get("/my-perms")
def my_perms(request: Request):
    return ORJSONResponse({
        "title": "My Permissions",
        "pre": "/links",
        "data": f"""
        <pre>
            <strong>Permission Number</strong>: {request.state.member.perm}
            <strong>Role Name</strong>: {request.state.member.name}
            <strong>Can Access Lynx (limited)</strong>: {request.state.member.perm >= 2}
            <strong>Can Access Lynx (full)</strong>: {request.state.member.perm >= 4}
        </pre>
        """
    })

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

        <p>But if you're locked out of your discord account, just click the <pre>Reset Credentials</pre> button</p>

        <div id="verify-parent">
            <button id="verify-btn" onclick="reset()">Reset</button>
        </div>
        """
    })

@app.get("/loa")
def loa(request: Request):
    return ORJSONResponse({
        "title": "Leave Of Absense",
        "pre": "/links",
        "data": f"""
        <pre>
        Just a tip for those new to lynx

        1. Login to lynx
        2, Click Leave Of Absense
        3. Click 'Add Row'
        4. Fill out the nessesary fields
        5. Click 'Save'
        </pre>
        """
    })

@app.get("/links")
def links(request: Request):
    return ORJSONResponse({
        "title": "Some Useful Links",
        "data": f"""
        <pre>
        <a href="/my-perms">My Permissions</a>
        <a href="/reset">Lynx Credentials Reset</a>
        <a href="/loa">Leave Of Absense</a>
        <a href="/staff-apps">Staff Applications</a>
        <a href="/links">Some Useful Links</a>
        <a href="/staff-verify">Staff Verification</a> (in case you need it)
        <a href="/staff-guide">Staff Guide</a>
        <a href="/admin">Admin Console</a>
        <a href="/requests">Requests</a>
        </pre>
    """
    })

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