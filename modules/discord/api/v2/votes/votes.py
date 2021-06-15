from modules.core import *
from .models import APIResponse, BotVoteCheck, BotVote
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Votes"]
)

@router.get("/{bot_id}/votes", response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to check amount of votes a user or the whole bot has."""
    if user_id is None:
        votes = await db.fetchval("SELECT votes FROM bots WHERE bot_id = $1", bot_id)
        return {"votes": votes, "voted": votes != 0, "type": "BotVote", "reason": "No User ID set", "partial": True}
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    voter_ts = await db.fetchval("SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    voter_count = len(voter_ts) if voter_ts else 0
    ret = await vote_bot(user_id = user_id, bot_id = bot_id, autovote = False, test = False, pretend = True)
    if ret is None:
        return {"votes": voter_count, "voted": voter_count != 0, "type": "VNFVote", "reason": "Voter not found!", "partial": True}
    return {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": ret[0].timestamp() if isinstance(ret, tuple) else 0, "vts": voter_ts, "time_to_vote": ret[1].total_seconds() if isinstance(ret, tuple) else 0, "vote_right_now": ret == True, "type": "Vote", "reason": None, "partial": False}

@router.patch("/{bot_id}/votes")
async def create_vote(bot_id: int, data: BotVote, Authorization: str = Header("USER_TOKEN")):
    """Endpoint to create a vote for a bot"""
    id = await user_auth(data.user_id, Authorization)
    if id is None:
        return abort(401)

@router.post("/{bot_id}/votes/test")
async def send_test_webhook(bot_id: int, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to test webhooks"""
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    return await vote_bot(user_id = 519850436899897346, bot_id = bot_id, autovote = False, test = True, pretend = False)
