from modules.core import *

from ..base import API_VERSION
from .models import (APIResponse, BotPromotion, BotPromotions)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Promotions"]
)

@router.get(
    "/{bot_id}/promotions", 
    response_model = BotPromotions
)
async def get_promotion(request:  Request, bot_id: int):
    """Returns all the promotions for a bot on Fates List"""
    db = request.app.worker_session.postgres
    promos = await get_promotions(db, bot_id)
    if promos == []:
        return abort(404)
    return {"promotions": promos}

@router.post(
    "/{bot_id}/promotions",
    response_model = APIResponse, 
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def new_promotion(request: Request, bot_id: int, promo: BotPromotion):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic"""
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    await add_promotion(db, bot_id, promo.title, promo.info, promo.css, promo.type)
    await redis.delete(f"botcache-{bot_id}-True")
    await redis.delete(f"botcache-{bot_id}-False")
    return api_success()

@router.patch(
    "/{bot_id}/promotions/{id}", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def edit_promotion(request: Request, bot_id: int, promo: BotPromotion, id: uuid.UUID):
    """Edits an promotion for a bot given its promotion ID."""
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", id, bot_id)
    if pid is None:
        return api_error(
            "Promotion not found",
            status_code = 404
        )
    await db.execute(
        "UPDATE bot_promotions SET title = $1, info = $2, type = $3 WHERE bot_id = $4 AND id = $5", 
        promo.title, 
        promo.info, 
        promo.type,
        bot_id, 
        id
    )
    await redis.delete(f"botcache-{bot_id}-True")
    await redis.delete(f"botcache-{bot_id}-False")
    return api_success()

@router.delete(
    "/{bot_id}/promotions/{id}", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def delete_promotion(request: Request, bot_id: int, id: uuid.UUID):
    """Deletes a bots promotion"""
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", id)
    if eid is None:
        return api_error(
            "Promotion not found",
            status_code = 404
        )
    await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", bot_id, id)
    await redis.delete(f"botcache-{bot_id}-True")
    await redis.delete(f"botcache-{bot_id}-False")
    return api_success()
