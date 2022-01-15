import io

from starlette.responses import StreamingResponse
from fastapi import Response
from modules.core import constants
import bleach
import markdown
from lxml.html.clean import Cleaner

from ..core import *

cleaner = Cleaner()

router = APIRouter(
    tags = ["Servers"],
    include_in_schema = False
)

@router.get("/_sunbeam/pub/server/{guild_id}/reviews_html")
async def guild_review_page(request: Request, guild_id: int, page: int = 1):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session, guild_id, page=page, target_type=enums.ReviewType.server)
    context = {
        "id": str(guild_id),
        "type": "server",
        "reviews": {
            "average_rating": float(reviews[1])
        },
        "index": "/servers"
    }
    data = {
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4],
    }

    user = {}
    
    return await templates.TemplateResponse("ext/reviews.html", {"request": request, "data": {"user": user}} | data, context = context)

