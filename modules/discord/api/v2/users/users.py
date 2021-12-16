from lxml.html.clean import Cleaner

from modules.core import *
from modules.core.classes import User as _User

from ..base import API_VERSION
from .models import APIResponse, BotMeta, enums, BaseUser, UpdateUserPreferences, OwnershipTransfer, BotAppeal

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
async def fetch_user(request: Request, user_id: int, bot_logs: bool = False, system_bots: bool = False, worker_session = Depends(worker_session)):
    user = await _User(id = user_id, db = worker_session.postgres).profile(bot_logs=bot_logs, system_bots=system_bots)
    if not user:
        return abort(404)
    return user

@router.patch(
    "/{user_id}/token",
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def regenerate_user_token(request: Request, user_id: int):
    await db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(132), user_id)
    return api_success()

@router.patch(
    "/{user_id}/preferences",
    dependencies = [
        Depends(user_auth_check)
    ],
    operation_id="update_user_preferences"
)
async def update_user_preferences(request: Request, user_id: int, data: UpdateUserPreferences):
    if data.user_id and data.user_id != user_id:
        admin = (await is_staff(staff_roles, user_id, 4))[0]
        if not admin:
            return abort(403)
        user_id = data.user_id
    else:
        state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", user_id)
        if state in (enums.UserState.global_ban, enums.UserState.profile_edit_ban):
            return api_error("You have been banned from using this API endpoint")

    if data.js_allowed is not None:
        await db.execute("UPDATE users SET js_allowed = $1 WHERE user_id = $2", data.js_allowed, user_id)
        request.session["js_allowed"] = data.js_allowed
    if data.description is not None:
        await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", data.description, user_id)
    if data.user_css is not None:
        await db.execute("UPDATE users SET user_css = $1 WHERE user_id = $2", data.user_css, user_id)
    if data.profile_css is not None:
        await db.execute("UPDATE users SET profile_css = $1 WHERE user_id = $2", data.profile_css, user_id)
    return api_success()

@router.get(
    "/{user_id}/username",
)
async def get_username_db(request: Request, user_id: int):
    return {"username": await db.fetchval("SELECT username FROM users WHERE user_id = $1", user_id)}

@router.get(
    "/{user_id}/obj",
    response_model = BaseUser,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=30, seconds=3),
                operation_bucket="fetch_user_obj"
            )
        )    
    ],
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
async def add_bot(request: Request, user_id: int, bot_id: int, bot: BotMeta, worker_session = Depends(worker_session)):
    """
    Adds a bot to fates list
    """
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_adder = BotActions(worker_session.postgres, bot_dict)
    rc = await bot_adder.add_bot()
    if rc is None:
        return api_success()
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
    Edits a bot, the owner here must be the owner editing the bot.
    """
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_editor = BotActions(db, bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return api_success()
    return api_error(rc)

@router.delete(
    "/{user_id}/bots/{bot_id}", 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=1, minutes=5),
                operation_bucket = "delete_bot"
            )
        ),
        Depends(user_auth_check)
    ],
    operation_id="delete_bot"
)
async def delete_bot(request: Request, user_id: int, bot_id: int):
    """Deletes a bot."""
    check = await db.fetchval("SELECT main FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if not check:
        state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        if state in (enums.BotState.approved, enums.BotState.certified):
            return api_error(
                "You aren't the owner of this bot. Only main bot owners may delete bots and staff may only delete bots once they have been unverified/denied/banned"
            )
        
    lock = await db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", bot_id)
    lock = enums.BotLock(lock)
    if lock != enums.BotLock.unlocked:
        return api_error(
            f"This bot cannot be deleted as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff locked, join the support server and run +unlock <BOT> to unlock it."
        )
    await db.execute("DELETE FROM bots WHERE bot_id = $1", bot_id)
    await db.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)
    await db.execute("DELETE FROM reviews WHERE target_id = $1 AND target_type = $2", bot_id, enums.ReviewType.bot)

    # Check all packs
    packs = await db.fetch("SELECT bots FROM bot_packs")
    pack_bot_delete = [] # Packs to delete the bot from
    for pack in packs:
        if bot_id in pack["bots"]:
            pack_bot_delete.append((pack["id"], [id for id in pack["bots"] if id in pack["bots"]])) # Get all bots in pack, then delete them all uaing executemany
    await db.executemany("UPDATE bot_packs SET bots = $2 WHERE id = $1", pack_bot_delete)

    delete_embed = discord.Embed(title="Bot Deleted :(", description=f"<@{user_id}> has deleted the bot <@{bot_id}>!", color=discord.Color.red())
    msg = {"content": "", "embed": delete_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
    await redis_ipc_new(redis_db, "SENDMSG", msg=msg, timeout=None)

    await bot_add_event(bot_id, enums.APIEvents.bot_delete, {"user": user_id})    
    return api_success(status_code = 202)

@router.patch(
    "/{user_id}/bots/{bot_id}/ownership",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=1, minutes=5)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def transfer_bot_ownership(request: Request, user_id: int, bot_id: int, transfer: OwnershipTransfer):
    transfer.new_owner = int(transfer.new_owner)
    head_admin, _, _ = await is_staff(staff_roles, user_id, 6)
    main_owner = await db.fetchval("SELECT main FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if not head_admin:
        if not main_owner:
            return api_error(
                "You aren't the owner of this bot. Only main bot owners and head admins may transfer bot ownership"
            )
    
        count = await db.fetchval("SELECT bot_id FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, transfer.new_owner)
        if not count:
            return api_error(
                "This owner first must be listed in extra owners in order to transfer ownership to them"
            )
            
    elif not main_owner:
        check = await is_staff_unlocked(bot_id, user_id)
        if not check:
            return api_error(
                "You must staff unlock this bot to transfer ownership"
            )
    
    check = await get_user(transfer.new_owner)
    if not check:
        return api_error(
            "Specified user is not an actual user"
        )

    lock = await db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", int(bot_id))
    lock = enums.BotLock(lock)
    if lock != enums.BotLock.unlocked:
        return api_error(f"This bot cannot be edited as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff staff locked, join the support server and run +unlock <BOT> to unlock it.")

    async with db.acquire() as conn:
        async with conn.transaction() as tr:
            await conn.execute("UPDATE bot_owner SET main = false WHERE main = true AND bot_id = $1", bot_id)
            await conn.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, transfer.new_owner, True)
    
    embed = discord.Embed(title="Bot Ownership Transfer", description=f"<@{user_id}> has transferred ownership of bot <@{bot_id}> to <@{transfer.new_owner}>!", color=discord.Color.green())
    msg = {"content": "", "embed": embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
    await redis_ipc_new(redis_db, "SENDMSG", msg=msg, timeout=None)
    await bot_add_event(bot_id, enums.APIEvents.bot_transfer, {"user": user_id, "new_owner": transfer.new_owner})    
    return api_success()

@router.post(
    "/{user_id}/bots/{bot_id}/appeal",
    response_model=APIResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(user_auth_check)
    ],
    operation_id="appeal_bot"
)
async def appeal_bot(request: Request, bot_id: int, data: BotAppeal):
    if len(data.appeal) < 7:
        return api_error(
            "Appeal must be at least 7 characters long"
        )
    db = request.app.state.worker_session.postgres

    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)

    if state == enums.BotState.denied:
        title = "Bot Resubmission"
        appeal_title = "Context"
    elif state == enums.BotState.banned:
        title = "Ban Appeal"
        appeal_title = "Appeal"
    else:
        return api_error(
            "You cannot send an appeal for a bot that is not banned or denied!"
        )
    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    bot = await get_bot(bot_id)
    resubmit_embed.add_field(name="Username", value = bot['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bot_id))
    resubmit_embed.add_field(name="Resubmission", value = str(state == enums.BotState.denied))
    resubmit_embed.add_field(name=appeal_title, value = data.appeal)
    msg = {"content": f"<@&{staff_ping_add_role}>", "embed": resubmit_embed.to_dict(), "channel_id": str(appeals_channel), "mention_roles": [str(staff_ping_add_role)]}
    await redis_ipc_new(request.app.state.worker_session.redis, "SENDMSG", msg=msg, timeout=None)
    return api_success()
