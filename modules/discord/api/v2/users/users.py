from lxml.html.clean import Cleaner

from modules.core import *
from modules.core.classes import User as _User

from ..base import API_VERSION
from .models import APIResponse, BotMeta, enums, BaseUser, UserDescEdit, UserJSPatch

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Users"]
)

@router.get(
    "/{user_id}",
    operation_id="fetch_user"
)
async def fetch_user(request: Request, user_id: int, worker_session = Depends(worker_session)):
    user = await _User(id = user_id, db = worker_session.postgres, client = worker_session.discord.main).profile()
    if not user:
        return abort(404)
    return user

@router.patch(
    "/users/{user_id}/description", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ],
    operation_id="set_user_description"
)
async def set_user_description(request: Request, user_id: int, desc: UserDescEdit):
    await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", desc.description, user_id)
    return api_success()

@router.patch(
    "/users/{user_id}/token", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def regenerate_user_token(request: Request, user_id: int):
    """Regenerate the User API token
    ** User API Token**: You can get this by clicking your profile and scrolling to the bottom and you will see your API Token
    """
    await db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(132), user_id)
    return api_success()

@router.patch(
    "/users/{user_id}/js_allowed",
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def set_js_mode(request: Request, user_id: int, data: UserJSPatch):
    await db.execute("UPDATE users SET js_allowed = $1", data.js_allowed)
    request.session["js_allowed"] = data.js_allowed
    return api_success()


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
