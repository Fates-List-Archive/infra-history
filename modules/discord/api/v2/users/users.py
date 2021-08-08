from lxml.html.clean import Cleaner

from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotMeta, enums, BaseUser

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Users"]
)

@router.get(
    "/{user_id}/obj",
    response_model = BaseUser
)
async def get_cache_user(request: Request, user_id: int):
    user = await get_any(user_id)
    if not user:
        return abort(404)
    return user

@router.put(
    "/{user_id}/bots/{bot_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=10, minutes=3)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def add_bot(request: Request, user_id: int, bot_id: int, bot: BotMeta):
    """
    Adds a bot to fates list. 
    
    Due to how Fates List adds and edits bots using RabbitMQ, this will return a 202 and not a 200 on success
    """
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_adder = BotActions(bot_dict)
    rc = await bot_adder.add_bot()
    if rc is None:
        return api_success(f"{site_url}/bot/{bot_id}", status_code = 202)
    return api_error(rc)

@router.patch(
    "/{user_id}/bots/{bot_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=3)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def edit_bot(request: Request, user_id: int, bot_id: int, bot: BotMeta):
    """
    Edits a bot, the owner here should be the owner editing the bot.
    Due to how Fates List edits bota using RabbitMQ, this will return a 202 and not a 200 on success
    """
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_editor = BotActions(bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return api_success(status_code = 202)
    return api_error(rc)

@router.delete(
    "/{user_id}/bots/{bot_id}", 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=1, minutes=5)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def delete_bot(request: Request, user_id: int, bot_id: int):
    """Deletes a bot you are the main owner of. Authorized staff should be using bot admin ops instead"""
    check = await db.fetchval("SELECT main FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if not check:
        return api_error(
            "You aren't the owner of this bot. Only bot owners may delete bots"
        )
    lock = await db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", bot_id)
    lock = enums.BotLock(lock)
    if lock != enums.BotLock.unlocked:
        return api_error(
            f"This bot cannot be deleted as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff locked, join the support server and run +unlock <BOT> to unlock it."
        )
    await add_rmq_task("bot_delete_queue", {"user_id": user_id, "bot_id": bot_id})
    return api_success(status_code = 202)
