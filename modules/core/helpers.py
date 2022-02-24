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

# Reviews

async def parse_reviews(worker_session, target_id: int, rev_id: uuid.uuid4 = None, page: int = None, recache: bool = False, in_recache: bool = False, target_type: enums.ReviewType = enums.ReviewType.bot, recache_from_rev_id: bool = False) -> List[dict]:
    db = worker_session.postgres
    if recache:
        async def recache(target_id: int):
            target_type = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", target_id)
            if not target_type:
                target_type = enums.ReviewType.server
            else:
                target_type = enums.ReviewType.bot

            logger.warning(str(target_id) + str(target_type))

            reviews = await _parse_reviews(worker_session, target_id, target_type=target_type)
            page_count = reviews[2]
            for page in range(0, page_count):
                await parse_reviews(worker_session, target_id, page = page if page else None, in_recache = True, target_type=target_type)
            # Edge case: ensure page 1 is always up to date
            await parse_reviews(worker_session, target_id, page = 1, in_recache = True, target_type=target_type)
        asyncio.create_task(recache(target_id))
        return

    if not isinstance(target_type, int):
        target_type = target_type.value

    if not in_recache:
        reviews = await worker_session.redis.get(f"review-{target_id}-{page}-{target_type}")
    else:
        reviews = None

    if reviews:
        return orjson.loads(reviews)
    reviews = await _parse_reviews(worker_session, target_id, rev_id = rev_id, page = page, target_type=target_type)
    await worker_session.redis.set(f"review-{target_id}-{page}-{target_type}-v2", orjson.dumps(reviews), ex=60*60*4)
    return reviews


async def _parse_reviews(worker_session, target_id: int, rev_id: uuid.uuid4 = None, page: int = None, target_type: str = enums.ReviewType.bot) -> List[dict]:
    db = worker_session.postgres

    per_page = 9
    if not rev_id:
        reply = False    
        rev_check = "" # Extra string to check review
        rev_args = () # Any extra arguments?
    else:
        reply = True
        rev_check = "AND id = $4" # Extra string to check for review id
        rev_args = (rev_id,) # Extra argument of review id

    if page is None:
        end = ""
    else:
        end = f"OFFSET {per_page*(page-1)} LIMIT {per_page}"
    reviews = await db.fetch(f"SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM reviews WHERE target_id = $1 AND target_type = $2 AND reply = $3 {rev_check} ORDER BY epoch, star_rating ASC {end}", target_id, target_type, reply, *rev_args)
    i = 0
    stars = 0
    while i < len(reviews):
        reviews[i] = dict(reviews[i])
        if reviews[i]["epoch"] in ([], None):
            reviews[i]["epoch"] = [time.time()]
        else:
            reviews[i]["epoch"].sort(reverse = True)
        reviews[i]["id"] = str(reviews[i]["id"])
        reviews[i]["user"] = await get_user(reviews[i]["user_id"], worker_session = worker_session)
        reviews[i]["user_id"] = str(reviews[i]["user_id"])
        reviews[i]["star_rating"] = float(round(reviews[i]["star_rating"], 2))
        reviews[i]["replies"] = []
        reviews[i]["review_upvotes"] = [str(ru) for ru in reviews[i]["review_upvotes"]]
        reviews[i]["review_downvotes"] = [str(rd) for rd in reviews[i]["review_downvotes"]]
        if not rev_id:
            stars += reviews[i]["star_rating"]
        for review_id in reviews[i]["_replies"]:
            _parsed_reply = await _parse_reviews(worker_session, target_id, review_id, target_type=target_type)
            try:
                reviews[i]["replies"].append(_parsed_reply[0][0])
            except:
                pass
        del reviews[i]["_replies"]
        i+=1
    total_rev = await db.fetchrow("SELECT COUNT(1) AS count, AVG(star_rating)::numeric(10, 2) AS avg FROM reviews WHERE target_id = $1 AND reply = false AND target_type = $2", target_id, target_type)

    if i == 0:
        return reviews, 10.0, 0, 0, per_page
    logger.trace(f"Total reviews per page is {total_rev['count']/per_page}")
    return reviews, float(total_rev["avg"]), int(total_rev["count"]), int(math.ceil(total_rev["count"]/per_page)), per_page