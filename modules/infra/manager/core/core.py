import asyncio
import datetime
import os
import pprint
import time
import uuid
from copy import deepcopy
from http import HTTPStatus
from typing import Optional, Union

import aiohttp
import discord
import orjson
from aenum import Enum, IntEnum
from discord import Color, Embed, Member, User
from loguru import logger

from config import ag_role, log_channel, main, manager_key, site_url, staff, testing
from modules.core.ipc import redis_ipc_new
from modules.core.permissions import StaffMember
from modules.models.enums import BotState, Status, UserState


async def set_cmd_perm(bot, guild, name, perm):
    ...


# Disnake/dpy2.0 interaction wrapper (to make life easier)
class InteractionWrapper:
    def __init__(self, interaction, ephemeral: bool = False):
        self.interaction = interaction
        asyncio.create_task(self.auto_defer(ephemeral))

    async def auto_defer(self, ephemeral: bool):
        start_time = time.time()
        while time.time(
        ) - start_time < 15 and not self.interaction.response.is_done():
            await asyncio.sleep(0)
        await self.interaction.defer(ephemeral=ephemeral)

    async def send(self, *args, **kwargs):
        return await self.interaction.send(*args, **kwargs)


class MenuState(IntEnum):
    rot = 0  # Running or timed out
    cancelled = 1


class BotListView(discord.ui.View):
    def __init__(self, bot, inter, bots, action, select_menu):
        super().__init__()
        self.state = MenuState.rot
        self.bots = bots
        self.select_menu = select_menu(
            bot=bot,
            inter=inter,
            action=action,
            placeholder="Please choose the bot",
            options=[],
        )
        options = 0
        for bot in self.bots:
            username = bot["user"]["username"][:25]
            description = bot["description"][:50]

            self.select_menu.add_option(label=username,
                                        description=description,
                                        value=bot["user"]["id"])
            options += 1

            if options == 24:
                break

        self.select_menu.add_option(label="Not listed", value="-1")
        self.add_item(self.select_menu)


async def request(
    method: str,
    ctx,
    url: str,
    dragon_auth: bool = True,
    user_token: Optional[str] = None,
    **kwargs,
):
    url = f"http://127.0.0.1:9999{url}"
    logger.info(f"Request init to {url}")
    if "headers" in kwargs:
        headers = kwargs["headers"]
    else:
        headers = {}

    headers["FL-API-Version"] = "2"
    async with aiohttp.ClientSession() as sess:
        f = getattr(sess, method.lower())
        async with f(url,
                     json=kwargs.get("json"),
                     headers=headers,
                     timeout=kwargs.get("timeout"),
                     max_redirects=30) as res:
            res_json = await res.json()
            logger.info(
                f"Request\n\nURL - {url}\nResponse - {res.status}\n{pprint.pformat(res_json)}"
            )
            return res.status, res_json


class MiniContext:
    """Mini Context to satisy some commands"""

    def __init__(self, member, bot):
        self.author = member
        self.bot = bot
        self.guild = member.guild

    async def send(self, *args, **kwargs):
        return await self.author.send(*args, **kwargs)

    async def kick(self, *args, **kwargs):
        return await self.author.kick(*args, **kwargs)

    async def ban(self, *args, **kwargs):
        return await self.author.ban(*args, **kwargs)


async def is_staff(ctx, user_id: int, min_perm: int = 2):
    res = await request("GET",
                        ctx,
                        f"/api/is_staff?user_id={user_id}&min_perm={min_perm}",
                        staff=False)
    res = res[1]
    return res["staff"], res["perm"], StaffMember(**res["sm"])


async def profile(ctx, user):
    """Gets the users profile, sends a message and returns None if not found"""
    if user.bot:
        return None
    res = await request("GET", ctx, f"/api/users/{user.id}", staff=False)
    if res[0] == 404:
        return None
    return res[1]


# usage: (_d, _h, _m, _s, _mils, _mics) = tdTuple(td)
def extract_time(td: datetime.timedelta) -> tuple:
    def _t(t, n):
        if t < n:
            return (t, 0)
        v = t // n
        return (t - (v * n), v)

    (s, h) = _t(td.seconds, 3600)
    (s, m) = _t(s, 60)
    return (td.days, h, m, s)


async def blstats(ctx):
    try:
        res = await request("GET",
                            ctx,
                            f"/api/blstats?workers=true",
                            staff=False)
    except Exception as exc:
        res = [
            502,
            {
                "uptime": 0,
                "pid": 0,
                "up": False,
                "server_uptime": 0,
                "bot_count": "Unknown",
                "bot_count_total": "Unknown",
                "error": f"{type(exc).__name__}: {exc} - Servers likely down",
                "workers": [0],
            },
        ]
    embed = Embed(title="Bot List Stats", description="Fates List Stats")
    uptime_tuple = extract_time(datetime.timedelta(seconds=res[1]["uptime"]))
    # ttvr = Time Till Votes Reset
    ttvr_tuple = extract_time(
        (datetime.datetime.now().replace(day=1, second=0, minute=0, hour=0) +
         datetime.timedelta(days=32)).replace(day=1) - datetime.datetime.now())
    uptime = "{} days, {} hours, {} minutes, {} seconds".format(*uptime_tuple)
    ttvr = "{} days, {} hours, {} minutes, {} seconds".format(*ttvr_tuple)
    embed.add_field(name="Uptime", value=uptime)
    embed.add_field(name="Time Till Votes Reset", value=ttvr)
    embed.add_field(name="Worker PID", value=str(res[1]["pid"]))
    embed.add_field(name="Worker Number",
                    value=res[1]["workers"].index(res[1]["pid"]) + 1)
    embed.add_field(
        name="Workers",
        value=f"{', '.join([str(w) for w in res[1]['workers']])} ({len(res[1]['workers'])} workers)",
    )
    embed.add_field(name="UP?", value=str(res[1]["up"]))
    embed.add_field(name="Server Uptime", value=str(res[1]["server_uptime"]))
    embed.add_field(name="Bot Count", value=str(res[1]["bot_count"]))
    embed.add_field(name="Bot Count (Total)",
                    value=str(res[1]["bot_count_total"]))
    embed.add_field(
        name="Errors",
        value=res[1]["error"]
        if res[1].get("error") else "No errors fetching stats from API",
    )
    return embed
