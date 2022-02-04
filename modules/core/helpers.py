"""
Helper functions for mundane tasks like getting maint, promotion or bot commands
and/or setting bot stats and voting for a bot. Also has replace tuples to be handled
"""

import json
import typing

import asyncpg
import aioredis
import bleach
import markdown
from modules.models import constants
from lxml.html.clean import Cleaner

from .auth import *
from .cache import *
from .events import *
from .imports import *
from .templating import *

from lynxfall.utils.string import ireplacem, intl_text

# Some replace tuples
# TODO: Move this elsewhere
js_rem_tuple = (("onclick", ""), ("onhover", ""), ("script", ""), ("onload", ""))
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

def flags_check(locks, check_locks):
    """Check if a particular lock is present in a bots locks"""
    if isinstance(check_locks, int):
        check_locks = [check_locks]
    locks_set = set(locks)
    check_locks_set = set([lock.value for lock in check_locks])
    if locks_set.intersection(check_locks_set):
        return True
    return False


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


async def default_server_desc(db: asyncpg.Pool, name: str, guild_id: int):
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


async def get_promotions(db: asyncpg.Pool, bot_id: int) -> list:
    api_data = await db.fetch(
        "SELECT id, title, info, css, type FROM bot_promotions WHERE bot_id = $1",
        bot_id,
    )
    return api_data


async def get_bot_commands(
    db: asyncpg.Pool,
    bot_id: int,
    lang: str,
    filter: Optional[str] = None
) -> dict:
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
            _cmd["id"] = str(_cmd["id"])
            for key in _cmd.keys():
                if isinstance(_cmd[key], str) and key in ("description",):
                    _cmd[key] = bleach.clean(
                        intl_text(
                            _cmd[key], lang
                        ),
                        strip=True,
                        tags=["a", "strong", "em"]
                    )

            cmd_dict[group].append(_cmd)
    return cmd_dict

async def add_promotion(
    db: asyncpg.Pool,
    bot_id: int, 
    title: str, 
    info: str, 
    css: str,
    type: int
):
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


async def invite_bot(
    db: asyncpg.Pool,
    redis: aioredis.Connection,
    bot_id: int, 
    user_id: int | None = None, 
    api: bool = False
):
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
        redis,
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
async def vanity_bot(db: asyncpg.Pool, redis: aioredis.Connection, vanity: str, ignore_prefix=False) -> Optional[list]:
    """Checks and returns the vanity of the bot, otherwise returns None"""

    if not ignore_prefix:
        if vanity in reserved_vanity or vanity.startswith("_"):  # Check if vanity is reserved and if so, return None
            return None

    cache = await redis.get(vanity + "-v1")
    if cache:
        data = cache.decode("utf-8").split(" ")
        type = enums.Vanity(int(data[0])).name
        if type == "server":
            type = "guild"
        return int(data[1]), type

    t = await db.fetchrow(
        "SELECT type, redirect FROM vanity WHERE lower(vanity_url) = $1",
        vanity.lower())  # Check vanity against database
    if t is None:
        return None  # No vanity found

    await redis.set(vanity, f"{t['type']} {t['redirect']}", ex=60 * 4)

    type = enums.Vanity(t["type"]).name  # Get type using Vanity enum
    if type == "server":
        type = "guild"
    return int(t["redirect"]), type


async def parse_index_query(
    worker_session,
    fetch: List[asyncpg.Record],
    type: enums.ReviewType = enums.ReviewType.bot,
    **kwargs
) -> list:
    """
    Parses a index query to a list of partial bots
    """
    db = worker_session.postgres
    lst = []
    for bot in fetch:
        banner_replace_tup = (
            ('"', ""),
            ("'", ""),
            ("http://", "https://"),
            ("file://", ""),
        )
        if bot.get("flags") and flags_check(bot["flags"], enums.BotFlag.system):
            continue
        if type == enums.ReviewType.server:
            bot_obj = dict(bot) | {
                "user":
                dict((await db.fetchrow(
                    "SELECT guild_id::text AS id, name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1",
                    bot["guild_id"],
                ))),
                "bot_id":
                str(bot["guild_id"]),
                "banner":
                ireplacem(banner_replace_tup, bot["banner"])
                if bot["banner"] else None,
            }
            bot_obj |= bot_obj["user"]
            if not bot_obj["description"]:
                bot_obj["description"] = await default_server_desc(
                    db,
                    bot_obj["user"]["username"], bot["guild_id"])
            lst.append(bot_obj)
        else:
            _user = await get_bot(bot["bot_id"], worker_session=worker_session)
            if _user:
                if _user.get("username", "").startswith("Deleted User "):
                    continue
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
    **kwargs
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
    base_query = f"SELECT flags, description, banner_card AS banner, state, votes, guild_count, {main_key}, nsfw FROM {table} {states}"
    if limit:
        end_query = f"LIMIT {limit}"
    else:
        end_query = ""
    logger.debug(base_query, add_query, end_query)
    fetch = await db.fetch(" ".join((base_query, add_query, end_query)))
    return await parse_index_query(worker_session, fetch, type=type, **kwargs)

def sanitize_bot(bot: dict, lang: str) -> dict:
    bot["description"] = bleach.clean(ireplacem(constants.long_desc_replace_tuple_sunbeam, intl_text(bot["description"], lang)), strip=True, tags=["strong", "em"])
    if bot["long_description_type"] == enums.LongDescType.markdown_pymarkdown: # If we are using markdown
        bot["long_description"] = emd(markdown.markdown(bot['long_description'], extensions = md_extensions))

    def _style_combine(s: str) -> list:
        """
        Given margin/padding, this returns margin, margin-left, margin-right, margin-top, margin-bottom etc.
        """
        return [s, s+"-left", s+"-right", s+"-top", s+"-bottom"]

    bot["long_description"] = bleach.clean(
        bot["long_description"], 
        tags=bleach.sanitizer.ALLOWED_TAGS+["span", "img", "iframe", "style", "p", "br", "center", "div", "h1", "h2", "h3", "h4", "h5", "section", "article", "fl-lang"], 
        strip=True, 
        attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES | {
            "iframe": ["src", "height", "width"], 
            "img": ["src", "alt", "width", "height", "crossorigin", "referrerpolicy", "sizes", "srcset"],
            "*": ["id", "class", "style", "data-src", "data-background-image", "data-background-image-set", "data-background-delimiter", "data-icon", "data-inline", "data-height", "code"]
        },
        styles=["color", "background", "background-color", "font-weight", "font-size"] + _style_combine("margin") + _style_combine("padding")
    )

    bot["long_description"] = intl_text(bot["long_description"], lang)
    bot["long_description"] = ireplacem(constants.long_desc_replace_tuple_sunbeam, bot["long_description"])
    return bot
