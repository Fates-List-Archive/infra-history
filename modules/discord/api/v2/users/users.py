from lxml.html.clean import Cleaner

from modules.core import *
from modules.core.classes import User as _User
from fastapi import APIRouter

from ..base import API_VERSION
from .models import APIResponse, IDResponse, BotMeta, BotPackPartial, enums, BaseUser, UpdateUserPreferences, OwnershipTransfer, BotAppeal, BotVoteCheck

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
    db: asyncpg.Pool = request.app.state.worker_session.postgres
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
    db: asyncpg.Pool = request.app.state.worker_session.postgres
    state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", user_id)
    if state in (enums.UserState.global_ban, enums.UserState.profile_edit_ban):
        return api_error("You have been banned from using this API endpoint")

    if data.description is not None:
        await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", data.description, user_id)
    if data.user_css is not None:
        await db.execute("UPDATE users SET user_css = $1 WHERE user_id = $2", data.user_css, user_id)
    if data.profile_css is not None:
        await db.execute("UPDATE users SET profile_css = $1 WHERE user_id = $2", data.profile_css, user_id)
    if data.site_lang is not None:
        await db.execute("UPDATE users SET site_lang = $1 WHERE user_id = $2", data.site_lang.value, user_id)
    return api_success()

@router.get(
    "/{user_id}/obj",
    response_model = BaseUser,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=100, seconds=5),
                operation_bucket="fetch_user_obj"
            )
        )    
    ],
)
async def get_cache_user(request: Request, user_id: int):
    worker_session: FatesWorkerSession = request.app.state.worker_session
    user = await get_any(user_id, worker_session=worker_session)
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
async def add_bot(
    request: Request, 
    user_id: int, 
    bot_id: int, 
    bot: BotMeta
):
    """
    Adds a bot to fates list
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_adder = BotActions(worker_session, bot_dict)
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
async def edit_bot(
    request: Request, 
    user_id: int, 
    bot_id: int, 
    bot: BotMeta
):
    """
    Edits a bot, the owner here must be the owner editing the bot.
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_editor = BotActions(worker_session, bot_dict)
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
    worker_session: FatesWorkerSession = request.app.state.worker_session
    check = await worker_session.postgres.fetchval("SELECT main FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if not check:
        state = await worker_session.postgres.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        if state in (enums.BotState.approved, enums.BotState.certified):
            return api_error(
                "You aren't the owner of this bot. Only main bot owners may delete bots and staff may only delete bots once they have been unverified/denied/banned"
            )
        
    flags = await worker_session.postgres.fetchval("SELECT flags FROM bots WHERE bot_id = $1", bot_id)
    if flags_check(flags, (enums.BotFlag.edit_locked, enums.BotFlag.staff_locked)):
        return api_error(
            "This bot cannot be deleted as it has been locked. Join the support server and run /unlock <BOT> to unlock it."
        )
    await worker_session.postgres.execute("DELETE FROM bots WHERE bot_id = $1", bot_id)
    await worker_session.postgres.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)
    await worker_session.postgres.execute("DELETE FROM reviews WHERE target_id = $1 AND target_type = $2", bot_id, enums.ReviewType.bot)

    # Check all packs
    packs = await worker_session.postgres.fetch("SELECT bots FROM bot_packs")
    pack_bot_delete = [] # Packs to delete the bot from
    for pack in packs:
        if bot_id in pack["bots"]:
            pack_bot_delete.append((pack["id"], [id for id in pack["bots"] if id in pack["bots"]])) # Get all bots in pack, then delete them all uaing executemany
    await worker_session.postgres.executemany("UPDATE bot_packs SET bots = $2 WHERE id = $1", pack_bot_delete)

    delete_embed = discord.Embed(title="Bot Deleted :(", description=f"<@{user_id}> has deleted the bot <@{bot_id}>!", color=discord.Color.red())
    msg = {"content": "", "embed": delete_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
    await redis_ipc_new(worker_session.redis, "SENDMSG", msg=msg, timeout=None)

    await bot_add_event(bot_id, enums.APIEvents.bot_delete, {"user": user_id})    
    await worker_session.redis.delete(f"botpagecache:{bot_id}")
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
async def transfer_bot_ownership(
    request: Request, 
    user_id: int, 
    bot_id: int, 
    transfer: OwnershipTransfer
):
    """
    Transfers ownership of a bot. If you are staff, this requires
    a high enough permission level and for the bot in question to
    be staff unlocked first
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    transfer.new_owner = int(transfer.new_owner)
    head_admin, _, _ = await is_staff(staff_roles, user_id, 6)
    main_owner = await worker_session.postgres.fetchval(
        "SELECT main FROM bot_owner WHERE bot_id = $1 AND owner = $2", 
        bot_id, 
        user_id
    )
    if not head_admin:
        if not main_owner:
            return api_error(
                "You aren't the owner of this bot. Only main bot owners and head admins may transfer bot ownership"
            )
    
        count = await worker_session.postgres.fetchval(
            "SELECT bot_id FROM bot_owner WHERE bot_id = $1 AND owner = $2", 
            bot_id, 
            transfer.new_owner
        )
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

    flags = await worker_session.postgres.fetchval(
        "SELECT flags FROM bots WHERE bot_id = $1", 
        bot_id
    )
    if flags_check(flags, (enums.BotFlag.edit_locked, enums.BotFlag.staff_locked)):
        return api_error(
            "This bot cannot be edited as it has been locked. Join our support server and run /unlock <BOT> to unlock it."
        )

    async with worker_session.postgres.acquire() as conn:
        async with conn.transaction() as tr:
            await conn.execute(
                "UPDATE bot_owner SET main = false WHERE main = true AND bot_id = $1", 
                bot_id
            )
            await conn.execute(
                "INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", 
                bot_id, 
                transfer.new_owner, 
                True
            )
            await conn.execute(
                "INSERT INTO user_bot_logs (user_id, bot_id, action, context) VALUES ($1, $2, $3, $4)", 
                user_id, 
                bot_id, 
                enums.UserBotAction.transfer_ownership, 
                str(transfer.new_owner)
            )

    embed = discord.Embed(
        title="Bot Ownership Transfer", 
        description=f"<@{user_id}> has transferred ownership of bot <@{bot_id}> to <@{transfer.new_owner}>!", 
        color=discord.Color.green()
    )
    msg = {"content": "", "embed": embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
    await redis_ipc_new(worker_session.redis, "SENDMSG", msg=msg, timeout=None)
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

    check = await db.fetchrow("SELECT state, flags FROM bots WHERE bot_id = $1", bot_id)
    state = check["state"]
    flags = check["flags"]

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

    if flags_check(flags, enums.BotFlag.staff_locked):
        return api_error("You cannot send an appeal for a bot that is staff locked")

    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    bot = await get_bot(bot_id)
    resubmit_embed.add_field(name="Username", value = bot['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bot_id))
    resubmit_embed.add_field(name="Resubmission", value = str(state == enums.BotState.denied))
    resubmit_embed.add_field(name=appeal_title, value = data.appeal)
    msg = {"content": f"<@&{staff_ping_add_role}>", "embed": resubmit_embed.to_dict(), "channel_id": str(appeals_channel), "mention_roles": [str(staff_ping_add_role)]}
    await redis_ipc_new(request.app.state.worker_session.redis, "SENDMSG", msg=msg, timeout=None)
    return api_success()

@router.get(
    "/{user_id}/bots/{bot_id}/votes", 
    response_model = BotVoteCheck, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(bot_user_auth_check)
    ]
)
async def get_user_votes(request: Request, bot_id: int, user_id: int):
    """
    Endpoint to check amount of votes a user has.


    **votes** - The amount of votes the bot has.
    
    **voted** - Whether or not the user has *ever* voted for the bot.

    **vote_epoch** - The redis TTL of the users vote lock. This is not time_to_vote which is the
    elapsed time the user has waited since their last vote.
    
    **vts** - A list of timestamps that the user has voted for the bot on that has been recorded.

    **time_to_vote** - The time the user has waited since they last voted.

    **vote_right_now** - Whether a user can vote right now. Currently equivalent to `vote_epoch < 0`.
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    voter_ts = await worker_session.postgres.fetchval(
        "SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", 
        bot_id, 
        user_id
    )
    
    vote_epoch = await worker_session.redis.ttl(f"vote_lock:{user_id}")

    voter_count = len(voter_ts) if voter_ts else 0
    
    return {
        "votes": voter_count, 
        "voted": voter_count != 0, 
        "vote_epoch": vote_epoch, 
        "vts": voter_ts, 
        "time_to_vote": (60*60*8 - vote_epoch) if (vote_epoch > 0) else 0, 
        "vote_right_now": vote_epoch < 0, 
    }

async def pack_check(worker_session: FatesWorkerSession, user_id: int, pack: BotPackPartial, mode = "add"):
    bots = []

    if len(pack.bots) > 5:
        return api_error("Maximum bots in a pack is 5")

    for bot_id in pack.bots:
        id = bot_id.replace(" ", "")
        if not id: 
            continue
        
        try:
            id = int(id)
        except:
            return api_error(f"{bot_id} is not a valid Bot ID")
        check = await worker_session.postgres.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", id)
        if not check:
            return api_error(f"{bot_id} does not exist on Fates List")
        bots.append(id)
    
    if mode == "add":
        packs = await worker_session.postgres.fetch("SELECT id FROM bot_packs WHERE owner = $1", user_id)
        if len(packs) > 5:
            return api_error("Pack limit reached!")

    if pack.icon and not pack.icon.startswith("https://"):
        return api_error("Icon URL must start with https://")
    
    if pack.banner and not pack.banner.startswith("https://"):
        return api_error("Banner URL must start with https://")

    return bots

@router.post(
    "/{user_id}/packs",
    response_model=IDResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(user_auth_check)
    ],
)
async def create_bot_pack(request: Request, user_id: int, pack: BotPackPartial):
    """
    Creates a new bot pack on the list
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    bots = await pack_check(worker_session, user_id, pack)

    if not isinstance(bots, list):
        return bots

    id = await worker_session.postgres.fetchval(
        "INSERT INTO bot_packs (icon, banner, owner, bots, description, name) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
        pack.icon,
        pack.banner,
        user_id,
        bots,
        pack.description,
        pack.name
    )
    return api_success(id = str(id))

@router.patch(
    "/{user_id}/packs/{pack_id}",
    response_model=APIResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(user_auth_check)
    ],
)
async def update_bot_pack(request: Request, user_id: int, pack_id: uuid.UUID, pack: BotPackPartial):
    """
    Updates an existing bot pack on the list
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    bots = await pack_check(worker_session, user_id, pack, mode="edit")

    if not isinstance(bots, list):
        return bots
    
    check = await worker_session.postgres.fetchval(
        "SELECT id FROM bot_packs WHERE id = $1 AND owner = $2", 
        pack_id, 
        user_id
    )
    if not check:
        return abort(404)

    await worker_session.postgres.execute(
        "UPDATE bot_packs SET icon = $1, banner = $2, bots = $3, description = $4, name = $5 WHERE id = $6",
        pack.icon,
        pack.banner,
        bots,
        pack.description,
        pack.name,
        pack_id
    )
    return api_success()

@router.delete(
    "/{user_id}/packs/{pack_id}",
    response_model=APIResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(user_auth_check)
    ],
)
async def delete_bot_pack(request: Request, user_id: int, pack_id: uuid.UUID):
    """
    Deletes an existing bot pack on the list
    """
    worker_session: FatesWorkerSession = request.app.state.worker_session
    check = await worker_session.postgres.fetchval(
        "SELECT id FROM bot_packs WHERE id = $1 AND owner = $2", 
        pack_id, 
        user_id
    )
    if not check:
        return abort(404)

    await worker_session.postgres.fetchval(
        "DELETE FROM bot_packs WHERE id = $1",
        pack_id
    )
    return api_success()
