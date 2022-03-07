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

# Create the doc tree
doctree_dict = {"documentation": []}

def gen_doctree(path_split):
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
    gen_doctree(path_split)

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

print(doctree)

# The actual form
lynx_form_beta = """
<!DOCTYPE html>

<html>
  <head>
    <link
      href="https://fonts.googleapis.com/css?family=Lexend Deca"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.4.0/build/styles/a11y-light.min.css">
    <script src="//cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.4.0/build/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/RickStrahl/highlightjs-badge@master/highlightjs-badge.min.js"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://adminlte.io/themes/v3/plugins/jquery/jquery.min.js"></script>
    <script src="https://adminlte.io/themes/v3/plugins/bootstrap/js/bootstrap.bundle.min.js"></script>
    <script src="https://adminlte.io/themes/v3/dist/js/adminlte.min.js?v=3.2.0"></script>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"
      integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3"
      crossorigin="anonymous"
    />
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css"
    />
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.0.0/css/all.css"
    />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css?family=Source+Sans+Pro:300,400,400i,700&display=fallback"
    />
  </head>
  <body class="sidebar-mini sidebar-closed sidebar-collapse">
    <div class="wrapper">
      <nav class="main-header navbar navbar-expand navbar-white navbar-light">
        <ul class="navbar-nav">
          <li class="nav-item">
            <a class="nav-link" data-widget="pushmenu" href="#" role="button"
              ><i class="fas fa-bars"></i
            ></a>
          </li>
          <li class="nav-item d-none d-sm-inline-block">
            <a href="https://lynx.fateslist.xyz" class="nav-link">Home</a>
          </li>
          <li class="nav-item d-none d-sm-inline-block">
            <a href="https://lynx.fateslist.xyz/admin" class="nav-link">Admin</a>
          </li>
          <li class="nav-item d-none d-sm-inline-block">
            <a href="https://lynx.fateslist.xyz/bot-actions" class="nav-link">Bot Actions</a>
          </li>
          <li class="nav-item d-none d-sm-inline-block">
            <a href="https://lynx.fateslist.xyz/user-actions" class="nav-link">User Actions</a>
          </li>
        </ul>
        <ul class="navbar-nav ml-auto">
          <li class="nav-item dropdown">
            <a class="nav-link" data-toggle="dropdown" href="#"
              ><i class="far fa-bell"></i
              ><span class="badge badge-warning navbar-badge">0</span></a
            >
            <div class="dropdown-menu dropdown-menu-lg dropdown-menu-right">
              <span class="dropdown-header">No Announcements</span>
              <div class="dropdown-divider"></div>
				  
	<a href="#" class="dropdown-item">
	<i class="fas fa-envelope mr-2"></i> 1 new messages
	<span class="float-right text-muted text-sm">Test</span>
	</a>
	
	<div class="dropdown-divider"></div>
	<a href="#" class="dropdown-item dropdown-footer">See All Notifications</a>
            </div>
          </li>
          <li class="nav-item">
            <a class="nav-link" data-widget="fullscreen" href="#" role="button"
              ><i class="fas fa-expand-arrows-alt"></i
            ></a>
          </li>
          <!-- Extra Code To Add Secret Side Bar
          
          <li class="nav-item">
            <a
              class="nav-link"
              data-widget="control-sidebar"
              data-slide="true"
              href="#"
              role="button"
              ><i class="fas fa-th-large"></i
            ></a>
          </li>
          -->
        </ul>
      </nav>
      <aside class="main-sidebar sidebar-dark-primary elevation-4">
        <a href="/" class="brand-link"
          ><img
            src="https://api.fateslist.xyz/static/botlisticon.webp"
            alt="Fates Logo"
            class="brand-image img-circle elevation-3"
            style="opacity:.8"
          /><span class="brand-text font-weight-light">Fates List</span></a
        >
        <div class="sidebar">
          <div class="form-inline">
          </div>
          <nav class="mt-2">
            <ul
              class="nav nav-pills nav-sidebar flex-column"
              data-widget="treeview"
              role="menu"
              data-accordion="false"
            >
              <li class="nav-item">
                <a id="home-nav" href="https://lynx.fateslist.xyz/" class="nav-link">
                <i class="nav-icon fa-solid fa-house"></i>
                  <p>Home</p>
                </a>
              </li>
              <li class="nav-item">
                <a href="https://lynx.fateslist.xyz/admin" class="nav-link">
                <i class="nav-icon fa-solid fa-server"></i>
                  <p>Piccolo Admin</p>
                </a>
              </li>
              <li class="nav-item">
                <a id="staff-guide-nav" href="https://lynx.fateslist.xyz/staff-guide" class="nav-link">
                <i class="nav-icon fa-solid fa-rectangle-list"></i>
                  <p>Staff Guide</p>
                </a>
              </li>
              <li class="nav-item">
                <a id="staff-apps-nav" href="https://lynx.fateslist.xyz/staff-apps" class="nav-link">
                <i class="nav-icon fa-solid fa-rectangle-list"></i>
                  <p>Staff Applications</p>
                </a>
              </li>
              <li class="nav-item">
                <a id="links-nav" href="https://lynx.fateslist.xyz/links" class="nav-link">
                <i class="nav-icon fa-solid fa-link"></i>
                  <p>Links</p>
                </a>
              </li>
              <li id="admin-panel-nav" class="nav-item">
                <a id="admin-panel-nav-link" href="#" class="nav-link">
                  <i class="nav-icon fa-solid fa-candy-cane"></i>
                  <p>Admin Panel <i class="right fas fa-angle-left"></i></p>
                </a>
                <ul class="nav nav-treeview">
                  <li class="nav-item">
                    <a id="bot-actions-nav" href="https://lynx.fateslist.xyz/bot-actions" class="nav-link">
                    <i class="far fa-circle nav-icon"></i>
                    <p>
                        Bot Actions
                        <span class="right badge badge-info">Beta</span>
                      </p>
                    </a>
                  </li>
                  <li class="nav-item">
                    <a id="user-actions-nav" href="https://lynx.fateslist.xyz/user-actions" class="nav-link"
                      ><i class="far fa-circle nav-icon"></i>
                      <p>
                        User Actions
                        <span class="right badge badge-info">Beta</span>
                      </p></a
                    >
                  </li>
                </ul>
                %doctree%
              </li>
            </ul>
          </nav>
        </div>
      </aside>
      <div class="content-wrapper" style="min-height:490px">
        <div class="content-header">
          <div class="container-fluid">
            <div class="row mb-2">
              <div class="col-sm-6"><h1 class="m-0"><span id="title-full"><span id="title">Welcome To Lynx!</span></span></h1></div>
              <div class="col-sm-6">
                <ol class="breadcrumb float-sm-right" id="currentBreadPath">
                  <li class="breadcrumb-item"><a href="#">Home</a></li>
                </ol>
              </div>
            </div>
          </div>
        </div>
        <div class="content">
          <div class="container-fluid">
            <div id="verify-screen">
            </div>
          </div>
        </div>
      </div>
      <footer class="main-footer">
        <div class="float-right d-none d-sm-inline">Lynx Panel</div>
        <strong
          >Copyright © 2022
          <a href="https://fateslist.xyz">Fateslist.xyz</a>.</strong
        >
        All rights reserved.
      </footer>
      <div id="sidebar-overlay"></div>
    </div>
  </body>
  <script>
    // https://stackoverflow.com/a/46959528
    function title(str) {
        return str.replaceAll("_", " ").replace(/(^|\s)\S/g, function(t) { return t.toUpperCase() });
    }

    function docReady(fn) {
        // see if DOM is already available
        if (document.readyState === "complete" || document.readyState === "interactive") {
            // call on next available tick
            setTimeout(fn, 1);
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }    


    async function getNotifications() {
        let resp = await fetch("https://lynx.fateslist.xyz/_notifications");
        if(resp.ok) {
            let data = await resp.json();
            data.forEach(function(notif) {
                if(notif.acked_users.includes(data.user_id)) {
                    return;
                }
                if(notif.type == 'alert') {
                    document.querySelector("#verify-screen").innerHTML = `<h1>Notification</h1>${notif.message}<button onclick="() => window.location.reload()">Dismiss</button>`
                }
            })
        }
    }

    docReady(async function() {
        var currentURL = window.location.pathname
        console.log('Chnaging Breadcrumb Paths')

        var pathSplit = currentURL.split('/')

        var breadURL = ''

        pathSplit.forEach(el => {
            if(!el) {
                return
            }
            console.log(el)
            breadURL += `/${el}`
            var currentBreadPath = title(el.replace('-', ' '))
            $('#currentBreadPath').append(`<li class="breadcrumb-item active"><a href="${breadURL}">${currentBreadPath}</a></li>`)
        })

        currentURL = currentURL.replace('/', '') // Replace first

        currentURLID = '#' + currentURL.replaceAll('/', '-') + "-nav"
        if(currentURL == "") {
            currentURLID = "#home-nav"
        }

        if(currentURL == 'bot-actions') {
           document.querySelector("#admin-panel-nav").classList.add("menu-open")
        } else if(currentURL== 'user-actions') {
           document.querySelector("#admin-panel-nav").classList.add("menu-open")
        } 

        if(currentURLID.includes('docs')) {
           $('#docs-main-nav').toggleClass('menu-open')

           // Find the subnavs
           var tree = pathSplit[2]
           var navID = `#docs-${tree}-nav`
           $(navID).toggleClass('menu-open')
           console.log(navID)
        }

        try {
            document.querySelector(currentURLID).classList.add('active')
        } catch {
            console.log(`No active element found: ${currentURLID}`)
        }
    
        //setInterval(getNotifications, 5000)

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
        } else {
            let status = res.status

            if(status == 404) {
                status = `<h1>404</h1><h3>Page not found</h3>`
            } else {
                status = `<h1>${status}</h1>`
            }

            document.querySelector("#title-full").innerHTML = "Animus magic is broken today!"
            document.querySelectorAll(".content")[0].innerHTML = `${status}<h4><a href='/'>Index</a><br/><a href='/links'>Some Useful Links</a></h4>`
        }
    })
  </script>
  <style>
    .pre {
        white-space: pre-line;
        word-wrap: break-word;
    }

    button {
        display: block;
        width: 100px;
        background-color: red;
        color: white;
        border: none;
        border-radius: 5px;
        margin-top: 10px;
        padding: 10px;
    }

    #verify-btn {
        display: initial;
    }

    label {
        font-weight: bold;
        margin-bottom: 5px;
    }

    select {
        width: 100%;
        padding: 10px;
    }

    input {
        width: 100%;
        padding: 10px;
    }

    .header-anchor {
        display: none;
    }
    h2:hover > .header-anchor {
        display: initial;
    }
    h3:hover > .header-anchor {
        display: initial;
    }

    .info, .warning, .aonly, .guidelines, .generic {
        border: 3px solid;
        margin-bottom: 3px;
        padding: 3px;
    }

    .info:before {
        content: "Info";
        font-size: 26px;
        font-weight: bold;
        color: blue;
    }

    .guidelines:before {
        content: "Guidelines";
        font-size: 26px;
        font-weight: bold;
        color: green;
    }


    .warning:before {
        content: "Warning";
        font-size: 26px;
        font-weight: bold;
        color: red;
    }

    .generic {
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .aonly:before {
        content: "Admin Only!";
        font-size: 26px;
        font-weight: bold;
        color: yellow;
    }

    .info {
        border-color: blue;
        background-color: rgba(0, 0, 255, 0.1);
    }

    .warning {
        border-color: red;
        background-color: rgba(255, 0, 0, 0.1);
    }

    .generic {
        border-color: red;
        background-color: rgba(255, 20, 10, 0.1);
    }

    .aonly {
        border-color: yellow;
        background-color: rgba(255, 255, 0, 0.1);
    }

    .guidelines {
        border-color: green;
        background-color: rgba(255, 0, 0, 0.1);
    }
  </style>

<script>
  </script>

</html>
""".replace("%doctree%", doctree)

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
        lynx_form_html = lynx_form_beta.replace("%username%", "Not logged in")

        if request.url.path.startswith("/_"):
            return await call_next(request)

        if request.url.path.startswith(("/staff-guide", "/requests", "/links", "/roadmap", "/docs")) or request.url.path == "/":
            if request.headers.get("Frostpaw-Staff-Notify"):
                return await call_next(request)
            else:
                return HTMLResponse(lynx_form_html)
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

class NoCacher(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        #if request.url.path.startswith(("/admin", "/meta")) or request.headers.get("Frostpaw-Staff-Notify"):
        #    response.headers["Cache-Control"] = "no-store"
        response.headers["Cache-Control"] = "no-store"
        return response

admin = NoCacher(admin)

async def server_error(request, exc):
    return HTMLResponse(content="Error", status_code=exc.status_code)

app = FastAPI(routes=[
    Mount("/admin", admin), 
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
style="width: 100%; height: 200px; font-size: 20px !important; resize: none;"
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

@app.get("/staff-guide")
def staff_guide_route(request: Request):
    return ORJSONResponse({
        "title": "Staff Guide",
        "data": staff_guide,
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

        <p>But if you're locked out of your discord account, just click the 'Reset' button. It will do the same
        thing as <strong>/lynxreset</strong></p>

        <div id="verify-parent">
            <button id="verify-btn" onclick="reset()">Reset</button>
        </div>
        """,
        "script": """
            async function reset() {
                document.querySelector("#verify-btn").innerText = "Resetting...";

                let res = await fetch("/reset-creds", {
                    method: "POST",
                    credentials: 'same-origin',
                    headers: {
                        "Content-Type": "application/json"
                    },
                })

                if(res.ok) {
                    let json = await res.json()
                    document.querySelector("#verify-screen").innerHTML = `<h4>Done</h4>`
                } else {
                    let json = await res.json()
                    alert("Error: " + json.detail)
                    document.querySelector("#verify-btn").innerText = "Reset";
                }
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
    style="width: 100%; height: 200px; font-size: 20px !important; resize: none;"
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
    "script": f"""
        var csrfToken = "{csrf_token}"
    """ + 
    """
        function getBotId(id) {
            return document.querySelector(id+"-alt").value || document.querySelector(id).value
        }

        async function claim() {
            let botId = getBotId("#queue")
            let res = await fetch(`/bot-actions/claim?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function unclaim() {
            let botId = getBotId("#under_review_claim")
            let reason = document.querySelector("#under_review_claim-reason").value
            let res = await fetch(`/bot-actions/unclaim?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function approve() {
            let botId = getBotId("#under_review_approved")
            let reason = document.querySelector("#under_review_approved-reason").value
            let res = await fetch(`/bot-actions/approve?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
            if(res.ok) {
                // Now put the invite to the bot
                window.location.href = `https://discord.com/api/oauth2/authorize?client_id=${botId}&scope=bot&application.command&guild_id=${json.guild_id}`
            }
        }

        async function deny() {
            let botId = getBotId("#under_review_denied")
            let reason = document.querySelector("#under_review_denied-reason").value
            let res = await fetch(`/bot-actions/deny?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function ban() {
            let botId = getBotId("#ban")
            let reason = document.querySelector("#ban-reason").value
            let res = await fetch(`/bot-actions/ban?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function unban() {
            let botId = getBotId("#unban")
            let reason = document.querySelector("#unban-reason").value
            let res = await fetch(`/bot-actions/unban?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function certify() {
            let botId = getBotId("#certify")
            let reason = document.querySelector("#certify-reason").value
            let res = await fetch(`/bot-actions/certify?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function uncertify() {
            let botId = getBotId("#uncertify")
            let reason = document.querySelector("#uncertify-reason").value
            let res = await fetch(`/bot-actions/uncertify?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function unverify() {
            let botId = getBotId("#unverify")
            let reason = document.querySelector("#unverify-reason").value
            let res = await fetch(`/bot-actions/unverify?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function requeue() {
            let botId = getBotId("#requeue")
            let reason = document.querySelector("#requeue-reason").value
            let res = await fetch(`/bot-actions/requeue?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function resetVotes() {
            let botId = getBotId("#reset-votes")
            let reason = document.querySelector("#reset-votes-reason").value
            let res = await fetch(`/bot-actions/reset-votes?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        async function setFlag() {
            let botId = getBotId("#set-flag")
            let reason = document.querySelector("#set-flag-reason").value
            let flag = parseInt(document.querySelector("#flag").value)

            let url = "/bot-actions/set-flag"

            if(document.querySelector("#unset").checked) {
                url = "/bot-actions/unset-flag"
            }

            let res = await fetch(`${url}?csrf_token=${csrfToken}`, {
                method: "POST",
                credentials: 'same-origin',
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"bot_id": botId, "reason": reason, "context": flag}),
            })
            let json = await res.json()
            alert(json.detail)
        }

        docReady(() => {
            if(window.location.hash) {
                document.querySelector(`${window.location.hash}`).scrollIntoView()
            }
        })
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

@app.get("/links")
def links(request: Request):
    return ORJSONResponse({
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
            <a href="/roadmap">Our Roadmap</a><br/>
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
    """
    })

@app.get("/docs")
def docs_redir():
    return RedirectResponse("https://lynx.fateslist.xyz/docs/index")

@app.get("/docs/{page:path}")
def docs(page: str):
    if page.endswith(".md"):
        return RedirectResponse(f"/docs/{page[:-3]}")
    
    elif not page:
        return RedirectResponse("/docs/index")

    if not page.replace("-", "").replace("_", "").replace("/", "").isalnum():
        return ORJSONResponse({"detail": "Invalid page"}, status_code=404)
    
    try:
        with open(f"modules/infra/admin_piccolo/api-docs/{page}.md", "r") as f:
            md_data = f.read()
    except FileNotFoundError as exc:
        return ORJSONResponse({"detail": f"api-docs/{page}.md not found -> {exc}"}, status_code=404)

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
        "title": f"{page.split('/')[-1].replace('-', ' ').title()}",
        "data": f"""
{md.render(md_data).replace("<table", "<table class='table'").replace(".md", "")}

        <a href="/docs-src/{page}">View Source</a> 
        """,
        "script": """
            docReady(() => {
                if(window.location.hash) {
                    document.querySelector(`${window.location.hash}`).scrollIntoView()
                }

                hljs.highlightAll();

                window.highlightJsBadge();
            })
        """
    }

@app.get("/docs-src/{page:path}")
def docs_source(page: str):
    if not page.replace("-", "").replace("_", "").replace("/", "").isalnum():
        return ORJSONResponse({"detail": "Invalid page"}, status_code=404)
    
    try:
        with open(f"modules/infra/admin_piccolo/api-docs/{page}.md", "r") as f:
            md_data = f.read()
    except FileNotFoundError as exc:
        return ORJSONResponse({"detail": f"api-docs/{page}.md not found -> {exc}"}, status_code=404)

    return {
        "title": "Markdown Test",
        "data": f"""
<pre>{md_data}</pre>
        """
    }

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

@app.get("/_notifications")
async def notifications(request: Request):
    return await app.state.db.fetch("SELECT acked_users, message, type FROM lynx_notifications")

@app.get("/roadmap")
async def roadmap(request: Request):
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
        "title": "Roadmap",
        "pre": "/links",
        "data": md.render("""
## Votes (Item 1, tied to item 2)

Votes should have ways to stop complete automation. Possibly with addition of coins though

<blockquote class="quote">

<h5>Suggestion from staff</h5>
Nishant1500
</blockquote>

## Coins (Item 2)

Basic Information

Currency will be usable to:

1. Buy priority spots on the list (this will be hard coded in the code for now)
2. Priority approval of bots*

### How to earn it

- Server boosts
- awarded by staff for server activity
- adding or editing your bot (editing your bot too much for just getting currency may lead to a ban from currency system, adding will give more currency than edits)
- Keeping a good bot page
- Events
- sellix shop (purchasing coins)

*feel free to request large amount of fates currency for priority reviewing a bot or for bot developers requesting a specific reviewer etc*

## Some Ideas

- Each vote would give small number of coins to owner
- Votes will cost coins
- Coins will replenish/give you enough for one vote every eight hours
- Bronze User will be removed
- Being active in chat = More coins
- Many actions regarding coins (votes) will have cooldown to avoid people spamming
- Sellix webhook (NOT YET IMPLEMENTED)

        """)
    }

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
            docReady(() => {
                if(window.location.hash) {
                    document.querySelector(`${window.location.hash}`).scrollIntoView()
                }
            })

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
app.add_middleware(NoCacher)
