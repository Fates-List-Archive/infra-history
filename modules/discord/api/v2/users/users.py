from modules.core import *
from fastapi import APIRouter

from ..base import API_VERSION
from .models import APIResponse, IDResponse, BotMeta, BotPackPartial, enums, BaseUser, UpdateUserPreferences, OwnershipTransfer, BotAppeal, BotVoteCheck, UpdateVoteReminders

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Users"],
)

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