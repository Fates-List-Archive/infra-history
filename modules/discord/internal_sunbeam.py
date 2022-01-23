from ..core import *

router = APIRouter(tags=["Sunbeam - Internal HTML Routes"])

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

def gen_owner_html(owners_lst: tuple):
    owners_html = '<span class="iconify" data-icon="mdi-crown" data-inline="false" data-height="1.5em" style="margin-right: 3px"></span>'
    owners_html += "<br/>".join([f"<a class='long-desc-link' href='/profile/{owner[0]}'>{owner[1]}</a>" for owner in owners_lst if owner])
    return owners_html

@router.get("/_sunbeam/pub/bot/{bot_id}/reviews_html", dependencies=[Depends(id_check("bot"))])
async def bot_review_page(request: Request,
                          bot_id: int,
                          page: int = 1,
                          user_id: int | None = 0):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session,
                                  bot_id,
                                  page=page)
    context = {
        "id": str(bot_id),
        "type": "bot",
        "reviews": {
            "average_rating": float(reviews[1])
        },
        "user_id": str(user_id),
    }
    data = {
        "bot_reviews": reviews[0],
        "average_rating": reviews[1],
        "total_reviews": reviews[2],
        "review_page": page,
        "total_review_pages": reviews[3],
        "per_page": reviews[4],
    }

    bot_info = await get_bot(bot_id,
                             worker_session=request.app.state.worker_session)
    if bot_info:
        user = dict(bot_info)
        user["name"] = user["username"]

    else:
        return await templates.e(request, "Bot Not Found")

    return await templates.TemplateResponse(
        "ext/reviews.html",
        {
            "request": request,
            "data": {
                "user": user
            }
        } | data,
        context=context,
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