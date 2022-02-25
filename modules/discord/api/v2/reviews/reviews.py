from modules.core import *
from lynxfall.utils.string import intl_text

from ..base import API_VERSION
from .models import APIResponse, BotReviewPartial, BotReviewPartialExt, BotReviews, BotReviewVote

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Reviews"],
)

minlength = 10

@router.delete(
    "/users/{user_id}/reviews/{id}", 
    response_model = APIResponse,
    dependencies=[
        Depends(id_check("user")),
        Depends(user_auth_check)
    ]
)
async def delete_review(request: Request, user_id: int, id: uuid.UUID):
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    check = await db.fetchrow(
        "SELECT target_id, parent_id, target_type, star_rating FROM reviews WHERE id = $1 AND user_id = $2", 
        id, 
        user_id
    )
    
    if check is None:
        return abort(404)
    
    await db.execute("DELETE FROM reviews WHERE id = $1", id)
    
    await add_ws_event(
        redis,
        check["target_id"],
        {
            "m": {
                "e": enums.APIEvents.review_delete,
            },
            "ctx": {
                "user": str(user_id),
                "reply": check["parent_id"] is not None,
                "id": str(id),
                "star_rating": check["star_rating"]
            },
        },
        type="server" if check["target_type"] == enums.ReviewType.server else "bot"
    )

    return api_success()    

@router.patch(
    "/users/{user_id}/reviews/{rid}/votes", 
    response_model = APIResponse,
    dependencies = [
        Depends(id_check("user")),
        Depends(user_auth_check)
    ],
)
async def vote_review_api(request: Request, user_id: int, rid: uuid.UUID, vote: BotReviewVote):
    """Creates a vote for a review"""
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    bot_rev = await db.fetchrow("SELECT target_id, target_type, review_upvotes, review_downvotes, star_rating, parent_id FROM reviews WHERE id = $1", rid)
    if bot_rev is None:
        return api_error("You are not allowed to up/downvote this review (doesn't actually exist)")
    bot_rev = dict(bot_rev)
    if vote.upvote:
        main_key = "review_upvotes"
        remove_key = "review_downvotes"
    else:
        main_key = "review_downvotes"
        remove_key = "review_upvotes"
    if user_id in bot_rev[main_key]:
        return api_error("The user has already voted for this review")
    if user_id in bot_rev[remove_key]:
        while True:
            try:
                bot_rev[remove_key].remove(user_id)
            except:
                break
    bot_rev[main_key].append(user_id)
    await db.execute("UPDATE reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await add_ws_event(
        redis,
        bot_rev["target_id"], 
        {
            "m": {
                "e": enums.APIEvents.review_vote, 
            },
            "ctx": {
                "user": str(user_id), 
                "id": str(rid), 
                "star_rating": bot_rev["star_rating"], 
                "reply": bot_rev["parent_id"] is not None, 
                "upvotes": len(bot_rev["review_upvotes"]), 
                "downvotes": len(bot_rev["review_downvotes"]), 
                "upvote": vote.upvote
            },
        },
        type="server" if bot_rev["target_type"] == enums.ReviewType.server else "bot"
    )
        
    return api_success()
