from math import ceil

from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotVoteCheck

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Votes"]
)

@router.get(
    "/users/{user_id}/bots/{bot_id}/votes", 
    response_model = BotVoteCheck, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(bot_user_auth_check)
    ]
)
async def get_user_votes(request: Request, bot_id: int, user_id: int):
    """
    Endpoint to check amount of votes a user has.


    **votes** - The amount of votes the bot has.
    
    **voted** - Whether or not the user has *ever* voted for the bot.

    **vote_epoch** - The redis TTL of the users vote lock. This is not time_to_vote which is the
    elapsed time the user has waited since their last vote.
    
    **vts** - A list of timestamps that the user has voted for the bot on that has been recorded.

    **time_to_vote** - The time the user has waited since they last voted.

    **vote_right_now** - Whether a user can vote right now. Currently equivalent to `vote_epoch < 0`.
    """
    voter_ts = await db.fetchval(
        "SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", 
        bot_id, 
        user_id
    )
    
    vote_epoch = await redis_db.ttl(f"vote_lock:{user_id}")

    voter_count = len(voter_ts) if voter_ts else 0
    
    return {
        "votes": voter_count, 
        "voted": voter_count != 0, 
        "vote_epoch": vote_epoch, 
        "vts": voter_ts, 
        "time_to_vote": (60*60*8 - vote_epoch) if (vote_epoch > 0) else 0, 
        "vote_right_now": vote_epoch < 0, 
    }

