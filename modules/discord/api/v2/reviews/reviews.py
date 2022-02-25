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


async def new_review(request: Request, user_id: int, data: BotReviewPartialExt):
    """target_id is who the review is targetted to, target_type is whether its a guild or bot, 0 means bot, 1 means server"""
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    if data.target_type == enums.ReviewType.server:
        check = await db.fetchval("SELECT guild_id FROM servers WHERE guild_id = $1", data.target_id)
        if not check:
            return api_error("That server does not exist!")
    elif data.target_type == enums.ReviewType.bot:
        check = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", data.target_id)
        if not check:
            return api_error("That bot does not exist!")

    if len(data.review) < minlength:
        return api_error(
            f"Reviews must be at least {minlength} characters long"
        )

    if not data.reply:
        check = await db.fetchval(
            "SELECT id FROM reviews WHERE target_id = $1 AND target_type = $2 AND user_id = $3 AND reply = false", data.target_id, data.target_type, user_id
        )
    
        if check:
            return api_error(
                "You have already made a review for this bot/server, please edit that one instead of making a new one!",
                id=str(check)
            )
    else:
        check = await db.fetchval("SELECT id FROM reviews WHERE id = $1", data.id)
        if not check:
            return abort(404)
        
    id = uuid.uuid4()
    await db.execute(
        "INSERT INTO reviews (id, target_type, target_id, user_id, star_rating, review_text, epoch, reply) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        id,
        data.target_type,
        data.target_id, 
        user_id,
        data.star_rating, 
        data.review, 
        [time.time()],
        data.reply
    )
    
    if data.reply:
        await db.execute("UPDATE reviews SET replies = replies || $1 WHERE id = $2", [id], data.id)
        
    await add_ws_event(
        redis,
        data.target_id,
        {
            "m": {
                "e": enums.APIEvents.review_add,
            },
            "ctx": {
                "user": str(user_id), 
                "reply": data.reply,
                "id": str(id),
                "star_rating": data.star_rating,
                "review": data.review,
                "root": data.id
            },
        },
        type="server" if data.target_type == enums.ReviewType.server else "bot"
    )

    return api_success()


@router.patch(
    "/users/{user_id}/reviews/{id}", 
    response_model=APIResponse,
    dependencies=[
        Depends(id_check("user")),
        Depends(user_auth_check)
    ]
)
async def edit_review(request: Request, user_id: int, id: uuid.UUID, data: BotReviewPartial):
    """Deletes a review. Note that the (body) id, target_id, target_type and the reply flags are not honored for this endpoint"""
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    if len(data.review) < minlength:
        return api_error(
            f"Reviews must be at least {minlength} characters long"
        )

    check = await db.fetchrow(
        "SELECT parent_id, target_id, target_type FROM reviews WHERE id = $1 AND user_id = $2", 
        id,
        user_id,
    )
        
    if not check:       
        return abort(404)
        
    await db.execute(
        "UPDATE reviews SET star_rating = $1, review_text = $2, epoch = epoch || $3 WHERE id = $4", 
        data.star_rating, 
        data.review, 
        [time.time()],
        id
    )

    await add_ws_event(
        redis,
        check["target_id"],
        {
            "m": {
                "e": enums.APIEvents.review_edit,
            },
            "ctx": {
                "user": str(user_id),
                "reply": check["parent_id"] is not None,
                "id": str(id),
                "star_rating": data.star_rating,
                "review": data.review,
            },
        },
        type="server" if check["target_type"] == enums.ReviewType.server else "bot"
    )

    return api_success()
    
    
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
