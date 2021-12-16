from aioredis import Connection

from config._logger import logger

from .imports import *
from .system import redis_ipc_new


async def _user_fetch(
    user_id: str,
    user_type: int,
    user_only: bool = False,
    *, 
    worker_session = None
) -> Optional[dict]:
    """Internal function to fetch a user. If worker_sessiom is not explicitly specified, a warning will be logged"""
    if not worker_session:
        logger.debug("Using builtins is deprecated. Use worker session instead")
        redis = redis_db
    else:
        db = worker_session.postgres
        redis = worker_session.redis
    
    # Check if a suitable version is in the cache first before querying Discord

    CACHE_VER = 17 # Current cache ver

    if len(user_id) not in (17, 18, 19, 20): # Snowflake can be 17 - 20
        logger.debug(f"Ignoring blatantly wrong User ID: {user_id}")
        return None # This is impossible to actually exist on the discord API or on our cache

    # Query redis cache for some important info
    cache = await redis.hget(user_id, key = "cache") # This is bot in cache
    if cache: # We got a match
        cache = orjson.loads(cache)
        cache_time = time.time() - cache['epoch']
        if cache["fl_cache_ver"] != CACHE_VER or (not cache["valid_user"] and time.time() - cache_time > 60*20) or cache_time > 60*60*24:
            # Check for cache expiry
            logger.debug(f"Not using cache for id {user_id}")
        else:
            logger.debug(f"Using cache for id {user_id}") # Use cache
            fetch = False
            # Valid user and bot where bot is requested or all users requested
            if cache.get("valid_user") and ((user_type == 2 and cache["bot"]) or user_type == 3):
                fetch = True
                
            # Valid users and user where user is requested or all users requested
            elif cache.get("valid_user") and user_type == 1 and not cache["bot"]: 
                fetch = True
                
            if fetch: # We got a match
                if user_only:
                    return user_id, cache["username"]
                return cache | {
                    "id": user_id, 
                }
            return None # We got a bot, but not fitting in constraints

    logger.debug(f"Making API call to get user {user_id}")
    cmd_id = uuid.uuid4()
    data = await redis_ipc_new(redis, "GETCH", args=[str(user_id)])
    if data is None or data == b'-2':
        return None

    if data == b'-1':
        valid = False

    else:
        data = orjson.loads(data)
        valid = True

    cache = {"fl_cache_ver": CACHE_VER, "epoch": time.time(), "valid_user": valid}

    if valid:
        if data["bot"]: # Update cached username in postgres if valid username in asyncio background task
            try:
                await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(user_id), data["username"])
            except Exception:
                pass # Sometimes this cannot be done

        # Create cache and add to redis hash
        cache |= data
       
    # Add/Update redis
    await redis_db.hset(
        str(user_id),
        key = "cache",
        value = orjson.dumps(cache)
    ) 
    if not valid:
        return None

    fetch = False
    if (user_type == 2 and data["bot"]) or user_type == 3: # Same as when cached, see that for this
        fetch = True
    elif user_type == 1 and not data["bot"]:
        fetch = True
    if fetch:
        if user_only:
            return user_id, data["username"]
        return data | {
            "id": user_id
        } 
    return None

async def get_user(user_id: int, user_only = False, *, worker_session = None) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 1, user_only = user_only, worker_session = worker_session) # 1 means user

async def get_bot(user_id: int, user_only = False, *, worker_session = None) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 2, user_only = user_only, worker_session = worker_session) # 2 means bot

async def get_any(user_id: int, user_only = False, *, worker_session = None) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 3, user_only = user_only, worker_session = worker_session) # 3 means all
