import urllib.parse

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse
from fastapi.encoders import jsonable_encoder

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, SettingsPage

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)

@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    db = request.app.state.worker_session.postgres
    return await db.fetch("SELECT votes, epoch FROM bot_stats_votes_pm WHERE bot_id = $1", bot_id)