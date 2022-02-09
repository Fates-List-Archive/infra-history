import base64
from modules.core import *

from ..base import API_VERSION

router = APIRouter(
    prefix=f"/api/v{API_VERSION}/staff-apps",
    include_in_schema=True,
    tags=[f"API v{API_VERSION} - Staff Apps"],
)

@router.get("/qibli/{id}")
async def short_url(request: Request, id: uuid.UUID):
    """
    Gets the qibli data for a id
    """
    redis = request.app.state.worker_session.redis
    data = await redis.get(f"sapp:{id}")
    if not data:
        return abort(404)
    return orjson.loads(data)