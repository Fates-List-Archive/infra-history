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

from .auth import *
from .cache import *
from .imports import *

from lynxfall.utils.string import ireplacem, intl_text

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

def worker_session(request: Request):
    return request.app.state.worker_session

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

async def add_ws_event(redis: aioredis.Connection, target: int, ws_event: dict, *, id: Optional[uuid.UUID] = None, type: str = "bot", timeout: int | None = 30) -> None:
    """Create websocket event"""
    return # Being remade in baypaw

async def bot_get_events(*_, **__):
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    # Has been replaced by ws events
    return {}

async def bot_add_event(redis: aioredis.Connection, bot_id: int, event: int, context: dict, t: Optional[int] = None, *, send_event: bool = True, guild: bool = False):
    return # No point in using a broken API
