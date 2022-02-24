from modules.core import *
from modules.core.classes import User as _User, Profile
from fastapi import APIRouter

from ..base import API_VERSION, responses
from .models import APIResponse, IDResponse, BotMeta, BotPackPartial, enums, BaseUser, UpdateUserPreferences, OwnershipTransfer, BotAppeal, BotVoteCheck, UpdateVoteReminders

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Users"],
)

@router.get(
    "/{user_id}",
    operation_id="fetch_user",
    response_model = Profile,
)
async def fetch_user(request: Request, user_id: int, bot_logs: bool = False, system_bots: bool = False, worker_session = Depends(worker_session)):
    user = await _User(id = user_id, worker_session = worker_session).profile(bot_logs=bot_logs, system_bots=system_bots)
    if not user:
        return abort(404)
    return user

@router.patch(
    "/{user_id}/preferences",
    response_model=APIResponse,
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
    if data.vote_reminder_channel is not None:
        if not data.vote_reminder_channel.isdigit():
            return api_error("Vote reminder channel must be a valid channel ID")
        await db.execute("UPDATE users SET vote_reminder_channel = $1 WHERE user_id = $2", int(data.vote_reminder_channel), user_id)
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
