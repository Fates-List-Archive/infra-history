"""
Helper functions for mundane tasks like getting maint, promotion or bot commands
and/or setting bot stats and voting for a bot. Also has replace tuples to be handled
"""

import json
import re
import typing

import asyncpg
import bleach
from fastapi import datastructures
from lxml.html.clean import Cleaner

from .auth import *
from .cache import *
from .events import *
from .imports import *
from .templating import *


class PrettyJSONResponse(Response):
    media_type = "application/json"

    @staticmethod
    def render(content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


# Some replace tuples
# TODO: Move this elsewhere
js_rem_tuple = (("onclick", ""), ("onhover", ""), ("script", ""), ("onload",
                                                                   ""))
banner_replace_tuple = (
    ('"', ""),
    ("'", ""),
    ("http://", "https://"),
    ("(", ""),
    (")", ""),
    ("file://", ""),
)
ldesc_replace_tuple = (("window.location", ""), ("document.ge", ""))

cleaner = Cleaner(remove_unknown_tags=False)


def id_check(check_t: str):
    def check(id: int, fn: str):
        if id > INT64_MAX:
            raise HTTPException(status_code=400,
                                detail=f"{fn} out of int64 range")

    def bot(bot_id: int):
        return check(bot_id, "bot_id")

    def user(user_id: int):
        return check(user_id, "user_id")

    def server(guild_id: int):
        return check(guild_id, "guild_id")

    if check_t == "bot":
        return bot
    if check_t in ("guild", "server"):
        return server
    return user


async def default_server_desc(name: str, guild_id: int):
    name_split = name.split(" ")
    descs = (
        lambda: name +
        " is a great place to chill out and enjoy with friends!",
        lambda: name_split[0] + "? It's " + name + "!"
        if len(name_split) > 1 else random.choice(descs)(),
        lambda: "Interested in a good and friendly server, then " + name +
        " might be the best place for you!",
    )

    # For teo word servers, option 2 gives better results
    if len(name_split) in range(2, 4) and name_split[0].lower().replace(
            " ", "") not in ("the", ):
        desc = descs[1]()

    else:
        # Randomly choose one
        desc = random.choice(descs)()

    await db.execute("UPDATE servers SET description = $1 WHERE guild_id = $2",
                     desc, guild_id)
    return desc


def worker_session(request: Request):
    return request.app.state.worker_session


async def get_promotions(bot_id: int) -> list:
    api_data = await db.fetch(
        "SELECT id, title, info, css, type FROM bot_promotions WHERE bot_id = $1",
        bot_id,
    )
    return api_data


async def get_bot_commands(bot_id: int,
                           lang: str,
                           filter: Optional[str] = None) -> dict:
    await db.execute("DELETE FROM bot_commands WHERE cmd_groups = $1",
                     [])  # Remove unneeded commands
    if filter:
        extra = "AND name ilike $2"
        args = (f"%{filter}%", )
    else:
        extra, args = "", []
    cmd_raw = await db.fetch(
        f"SELECT id, cmd_groups, cmd_type, cmd_name, vote_locked, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE bot_id = $1 {extra}",
        bot_id,
        *args,
    )
    cmd_dict = {}
    for cmd in cmd_raw:
        for group in cmd["cmd_groups"]:
            if not cmd_dict.get(group):
                cmd_dict[group] = []
            _cmd = dict(cmd)
            for key in _cmd.keys():
                if isinstance(_cmd[key], str):
                    try:
                        _cmd[key] = (cleaner.clean_html(
                            intl_text(_cmd[key],
                                      lang)).replace("<p>",
                                                     "").replace("</p>", ""))
                    except Exception:
                        _cmd[key] = (bleach.clean(intl_text(
                            _cmd[key], lang)).replace("<p>",
                                                      "").replace("</p>", ""))
                elif isinstance(_cmd[key], list):
                    try:
                        _cmd[key] = [
                            cleaner.clean_html(intl_text(el, lang)).replace(
                                "<p>", "").replace("</p>", "")
                            for el in _cmd[key]
                        ]
                    except Exception:
                        _cmd[key] = [
                            bleach.clean(intl_text(el, lang)).replace(
                                "<p>", "").replace("</p>", "")
                            for el in _cmd[key]
                        ]

            cmd_dict[group].append(_cmd)
    return cmd_dict


async def add_maint(bot_id: int, type: int, reason: str):
    maints = await db.fetchrow(
        "SELECT bot_id FROM bot_maint WHERE bot_id = $1", bot_id)
    if maints is None:
        return await db.execute(
            "INSERT INTO bot_maint (bot_id, reason, type, epoch) VALUES ($1, $2, $3, $4)",
            bot_id,
            reason,
            type,
            time.time(),
        )
    await db.execute(
        "UPDATE bot_maint SET reason = $1, type = $2, epoch = $3 WHERE bot_id = $4",
        reason,
        type,
        time.time(),
        bot_id,
    )


async def add_promotion(bot_id: int, title: str, info: str, css: str,
                        type: int):
    if css is not None:
        css = css.replace("</style", "").replace("<script", "")
    info = info.replace("</style", "").replace("<script", "")
    return await db.execute(
        "INSERT INTO bot_promotions (bot_id, title, info, css, type) VALUES ($1, $2, $3, $4, $5)",
        bot_id,
        title,
        info,
        css,
        type,
    )


async def invite_bot(bot_id: int, user_id=None, api=False):
    bot = await db.fetchrow(
        "SELECT invite, invite_amount FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return None
    bot = dict(bot)
    if not bot["invite"] or bot["invite"].startswith("P:"):
        perm = (bot["invite"].split(":")[1].split("|")[0]
                if bot["invite"] and bot["invite"].startswith("P:") else 0)
        bot["invite"] = f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions={perm}&scope=bot%20applications.commands"
    if not api:
        await db.execute(
            "UPDATE bots SET invite_amount = $1 WHERE bot_id = $2",
            bot["invite_amount"] + 1,
            bot_id,
        )
    await add_ws_event(
        bot_id,
        {
            "m": {
                "e": enums.APIEvents.bot_invite
            },
            "ctx": {
                "user": str(user_id),
                "api": api
            },
        },
    )
    return bot["invite"]


# Check vanity of bot
async def vanity_bot(vanity: str) -> Optional[list]:
    """Checks and returns the vanity of the bot, otherwise returns None"""

    if vanity in reserved_vanity or vanity.startswith("_"):  # Check if vanity is reserved and if so, return None
        return None

    cache = await redis_db.get(vanity + "-v1")
    if cache:
        data = cache.decode("utf-8").split(" ")
        type = enums.Vanity(int(data[0])).name
        return int(data[1]), type

    t = await db.fetchrow(
        "SELECT type, redirect FROM vanity WHERE lower(vanity_url) = $1",
        vanity.lower())  # Check vanity against database
    if t is None:
        return None  # No vanity found

    await redis_db.set(vanity, f"{t['type']} {t['redirect']}", ex=60 * 4)

    type = enums.Vanity(t["type"]).name  # Get type using Vanity enum
    return int(t["redirect"]), type


async def parse_index_query(
    worker_session,
    fetch: List[asyncpg.Record],
    type: enums.ReviewType = enums.ReviewType.bot,
) -> list:
    """
    Parses a index query to a list of partial bots
    """
    lst = []
    for bot in fetch:
        banner_replace_tup = (
            ('"', ""),
            ("'", ""),
            ("http://", "https://"),
            ("file://", ""),
        )
        if type == enums.ReviewType.server:
            bot_obj = dict(bot) | {
                "user":
                await db.fetchrow(
                    "SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1",
                    bot["guild_id"],
                ),
                "bot_id":
                str(bot["guild_id"]),
                "banner":
                ireplacem(banner_replace_tup, bot["banner"])
                if bot["banner"] else None,
            }
            bot_obj |= bot_obj["user"]
            if not bot_obj["description"]:
                bot_obj["description"] = await default_server_desc(
                    bot_obj["user"]["username"], bot["guild_id"])
            lst.append(bot_obj)
        else:
            _user = await get_bot(bot["bot_id"], worker_session=worker_session)
            if _user:
                bot_obj = (dict(bot)
                           | {
                               "user":
                               _user,
                               "bot_id":
                               str(bot["bot_id"]),
                               "banner":
                               ireplacem(banner_replace_tup, bot["banner"])
                               if bot["banner"] else None,
                }
                    | _user)
                lst.append(bot_obj)
    return lst


async def do_index_query(
    worker_session,
    add_query: str = "",
    state: list = None,
    limit: Optional[int] = 12,
    type: enums.ReviewType = enums.ReviewType.bot,
) -> List[asyncpg.Record]:
    """
    Performs a 'index' query which can also be used by other things as well
    """
    if state is None:
        state = [0, 6]
    db = worker_session.postgres

    if type == enums.ReviewType.bot:
        table = "bots"
        main_key = "bot_id"
    else:
        table = "servers"
        main_key = "guild_id"

    states = "WHERE " + " OR ".join([f"state = {s}" for s in state])
    base_query = f"SELECT description, banner_card AS banner, state, votes, guild_count, {main_key}, nsfw FROM {table} {states}"
    if limit:
        end_query = f"LIMIT {limit}"
    else:
        end_query = ""
    logger.debug(base_query, add_query, end_query)
    fetch = await db.fetch(" ".join((base_query, add_query, end_query)))
    return await parse_index_query(worker_session, fetch, type=type)


async def vanity_check(id, vanity):
    """Check if a vanity exists or not given a id and a vanity"""
    if vanity.replace(" ", "") == "":
        return False
    vanity_check = await db.fetchrow(
        "SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2",
        vanity.replace(" ", "").lower(),
        id,
    )  # Get distinct vanitiss
    if (vanity_check is not None
            or vanity.replace("", "").lower() in reserved_vanity
            or "/" in vanity.replace("", "").lower()):
        return True
    return False


async def vanity_redirector(request: Request,
                            vanity: str,
                            ext,
                            extra_args=None,
                            ext_server=None):
    if vanity.isdigit():
        return RedirectResponse(f"/bot/{vanity}")
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] not in ("bot", "server"):
        return await templates.e(
            request,
            f"This is a {vurl[1]}. This is a work in progress :)",
            status_code=400,
        )
    if isinstance(ext, str):
        eurl = "/".join([site_url, vurl[1], str(vurl[0]), ext])
        return RedirectResponse(eurl)
    extra_args = extra_args if extra_args else {}
    if vurl[1] == "server":
        if not ext_server:
            return abort(404)
        return await ext_server(request=request,
                                guild_id=vurl[0],
                                **extra_args)
    return await ext(request=request, bot_id=vurl[0], **extra_args)
