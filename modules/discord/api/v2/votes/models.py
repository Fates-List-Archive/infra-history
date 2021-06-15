from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import APIResponse
from typing import Optional, List
import uuid

class BotVoteCheck(BaseModel):
    votes: int
    voted: bool
    vote_right_now: Optional[bool] = None
    vote_epoch: Optional[int] = None
    time_to_vote: Optional[int] = None
    type: str
    reason: Optional[str] = None
