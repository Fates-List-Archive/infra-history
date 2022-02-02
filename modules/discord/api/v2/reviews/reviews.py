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

@router.get(
    "/reviews/{target_id}/all", 
    response_model = BotReviews,
    dependencies=[
        Depends(
            Ratelimiter(global_limit=Limit(times=3, seconds=7))
        )
    ]
)
async def get_all_reviews(request: Request, target_id: int, target_type: enums.ReviewType, page: Optional[int] = 1, recache: bool = False):
    """Gets all reviews for a target bot or server/guild"""
    reviews = await parse_reviews(request.app.state.worker_session, target_id, page = page, target_type=target_type, in_recache=recache)
    if reviews[0] == []:
        return abort(404)
    return {
            "reviews": reviews[0],
            "average_stars": reviews[1],
            "pager": {
                "total_count": reviews[2], 
                "total_pages": reviews[3], 
                "per_page": reviews[4], 
                "from": ((page - 1) * reviews[4]) + 1, 
                "to": (page - 1) * reviews[4] + len(reviews[0])
            }
    }


@router.post(
        "/users/{user_id}/reviews", 
        response_model=APIResponse,
        dependencies=[
            Depends(id_check("user")),
            Depends(user_auth_check)
            ]
        )
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

    # Recache reviews
    await parse_reviews(
        request.app.state.worker_session, 
        data.target_id,
        recache = True,
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
    """Deletes a review. Note that the id and the reply flag is not honored for this endpoint"""
    db = request.app.state.worker_session.postgres
    redis = request.app.state.worker_session.redis
    if len(data.review) < minlength:
        return api_error(
            f"Reviews must be at least {minlength} characters long"
        )

    check = await db.fetchrow(
        "SELECT reply, target_id, target_type FROM reviews WHERE id = $1 AND user_id = $2", 
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
                "reply": check["reply"],
                "id": str(id),
                "star_rating": data.star_rating,
                "review": data.review,
            },
        },
        type="server" if check["target_type"] == enums.ReviewType.server else "bot"
    )

    # Recache reviews
    await parse_reviews(
        request.app.state.worker_session, 
        id, 
        recache = True,
        recache_from_rev_id=True
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
        "SELECT reply, replies, target_id, target_type, star_rating FROM reviews WHERE id = $1 AND user_id = $2", 
        id, 
        user_id
    )
    
    if check is None:
        return abort(404)
    
    await db.execute("DELETE FROM reviews WHERE id = $1", id)
    for review in check["replies"]:
        await db.execute("DELETE FROM reviews WHERE id = $1", review)
    
    await add_ws_event(
        redis,
        check["target_id"],
        {
            "m": {
                "e": enums.APIEvents.review_delete,
            },
            "ctx": {
                "user": str(user_id),
                "reply": check["reply"],
                "id": str(id),
                "star_rating": check["star_rating"]
            },
        },
        type="server" if check["target_type"] == enums.ReviewType.server else "bot"
    )

    # Recache reviews
    await parse_reviews(
        request.app.state.worker_session, 
        str(id), 
        recache = True,
        recache_from_rev_id=True
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
    bot_rev = await db.fetchrow("SELECT target_id, target_type, review_upvotes, review_downvotes, star_rating, reply FROM reviews WHERE id = $1", rid)
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
                "reply": bot_rev["reply"], 
                "upvotes": len(bot_rev["review_upvotes"]), 
                "downvotes": len(bot_rev["review_downvotes"]), 
                "upvote": vote.upvote
            },
        },
        type="server" if bot_rev["target_type"] == enums.ReviewType.server else "bot"
    )
    
    # Recache reviews
    await parse_reviews(
        request.app.state.worker_session,
        str(rid),
        recache = True,
        recache_from_rev_id=True
    )
    
    return api_success()
