from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse
from typing import Optional, List
import uuid

class BotRandom(BaseModel):
    """
    Represents a random bot on Fates List
    """
    bot_id: str
    description: str
    banner: str
    state: int
    username: str
    avatar: str
    servers: str
    invite: Optional[str] = None
    votes: int

class Bot(BaseUser):
    """
    Represents a bot on Fates List
    """
    description: str
    tags: list
    long_description_type: enums.LongDescType
    long_description: Optional[str] = None
    server_count: int
    shard_count: Optional[int] = 0
    user_count: int
    shards: Optional[list] = []
    prefix: str
    library: str
    invite: Optional[str] = None
    invite_link: str
    invite_amount: int
    owners: BotOwners
    features: list
    state: enums.BotState
    website: Optional[str] = None
    support: Optional[str] = None
    github: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: Optional[str] = None
    donate: Optional[str] = None
    privacy_policy: Optional[str] = None
    nsfw: bool
    banner: Optional[str] = None
