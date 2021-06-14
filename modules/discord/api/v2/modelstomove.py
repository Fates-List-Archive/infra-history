"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than aenum, pydantic, typing and uuid (typing and uuid is builtin)

Depends: enums.py
"""

from typing import List, Dict, Optional, ForwardRef, Union
from pydantic import BaseModel, validator
import uuid
import sys
sys.path.append("modules/models") # Libraries should remove this
import enums # as enums (for libraries)
import datetime
from .base_models import BaseUser, APIResponse

class BasePager(BaseModel):
    """Information given by the API for pagination"""
    total_count: int
    total_pages: int
    per_page: int
    from_: int
    to: int

    class Config:
        fields = {'from_': 'from'}

class BotMaintenancePartial(BaseModel):
    type: int = 1
    reason: Optional[str] = None

class BotMaintenance(BotMaintenancePartial):
    epoch: Optional[str] = None

BotReviewList = ForwardRef('BotReviewList')

class BotReview(BaseModel):
    id: uuid.UUID
    reply: bool
    user_id: str
    star_rating: float
    review: str
    review_upvotes: list
    review_downvotes: list
    flagged: bool
    epoch: list
    time_past: str
    user: BaseUser
    replies: Optional[BotReviewList] = []

class BotReviewList(BaseModel):
    """
    Represents a list of bot reviews on Fates List
    """
    __root__: List[BotReview]

class BotReviews(BaseModel):
    """Represents bot reviews and average stars of a bot on Fates List"""
    reviews: BotReviewList
    average_stars: float
    pager: BasePager

BotReview.update_forward_refs()
BotReviews.update_forward_refs()

class PrevResponse(BaseModel):
    """
    Represents a response from the Preview API
    """
    html: str

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

class BotOwner(BaseModel):
    user: BaseUser
    main: bool

class BotOwners(BaseModel):
    __root__: List[BotOwner]

class VoteReminderPatch(BaseModel):
    remind: bool

class BotPartial(BaseUser):
    description: str
    servers: str
    banner: str
    state: enums.BotState
    bot_id: str
    invite: Optional[str] = None
    nsfw: bool

class BotPartialList(BaseModel):
    __root__: List[BotPartial]

class BotEvent(BaseModel):
    m: dict
    ctx: dict

class BotEventList(BaseModel):
    __root__: List[BotEvent]

class BotEvents(BaseModel):
    events: BotEventList

class PartialBotCommand(BaseModel):
    cmd_type: enums.CommandType # 0 = no, 1 = guild, 2 = global
    cmd_groups: Optional[List[str]] = ["Default"]
    cmd_name: str
    friendly_name: str
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: Optional[str] = ""

class BotCommand(PartialBotCommand):
    id: uuid.UUID
    
class BotCommandAddResponse(APIResponse):
    id: uuid.UUID

class BotCommandsGet(BaseModel):
    __root__: Dict[str, List[BotCommand]]

class BotCommandDelete(BaseModel):
    """You can use either command id or cmd_name to remove a command"""
    id: Optional[uuid.UUID] = None
    cmd_name: Optional[str] = None
    
    @validator("cmd_name")
    def cmd_name_or_id_exists(cls, v, values, **kwargs):
        if not values["id"] or not v:
            raise ValueError("Either Command ID or UUID must be provided")
        return v

class BotVoteCheck(BaseModel):
    votes: int
    voted: bool
    vote_right_now: bool
    vote_epoch: int
    time_to_vote: int

class BotStats(BaseModel):
    guild_count: int
    shard_count: Optional[int] = None
    shards: Optional[list] = None
    user_count: Optional[int] = None

class BotVanity(BaseModel):
    type: str
    redirect: str

class User(BaseUser):
    id: str
    state: enums.UserState
    description: Optional[str] = None
    css: str

class PartialServer(BaseModel):
    icon: str
    name: str
    member_count: int
    created_at: str
    code: Optional[str] = None # Only in valid_servers

class PartialServerDict(BaseModel):
    __root__: Dict[str, PartialServer]

class AccessToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    current_time: Union[float, int]

class ServerList(BaseModel):
    servers: PartialServerDict

class ServerListAuthed(ServerList):
    access_token: AccessToken

class ServerCheck(BaseModel):
    scopes: str
    access_token: AccessToken

class UserDescEdit(BaseModel):
    description: str

class BotReviewAction(BaseModel):
    user_id: str

class BotReviewVote(BotReviewAction):
    upvote: bool

class Timestamp(BaseModel):
    __root__: int

class TimestampList(BaseModel):
    __root__: List[Timestamp]

class BotVotesTimestamped(BaseModel):
    timestamped_votes: Dict[str, TimestampList]

class FLFeature(BaseModel):
    type: str
    description: str

class FLTag(BaseModel):
    name: str
    iconify_data: str
    id: str

class FLTags(BaseModel):
    __root__: List[FLTag]

class BotIndex(BaseModel):
    tags_fixed: FLTags
    top_voted: BotPartialList
    certified_bots: BotPartialList
    new_bots: BotPartialList
    roll_api: str

class BaseSearch(BaseModel):
    tags_fixed: FLTags
    query: str

class BotSearch(BaseSearch):
    search_bots: BotPartialList
    profile_search: bool = False

class ProfilePartial(BaseUser):
    description: Optional[str] = None
    banner: None
    certified: Optional[bool] = False

class ProfilePartialList(BaseModel):
    __root__: List[ProfilePartial]

class ProfileSearch(BaseSearch):
    profiles: ProfilePartialList
    profile_search: bool = True

class ServersAdd(BaseModel):
    code: str
    description: str
    long_description_type: enums.LongDescType
    long_description: str
    tags: List[str]
    vanity: str
