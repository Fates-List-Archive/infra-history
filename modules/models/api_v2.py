"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than aenum, pydantic, typing and uuid (typing and uuid is builtin)

Depends: enums.py
"""

from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid
import sys
sys.path.append("modules/models") # Libraries should remove this
import enums # as enums (for libraries)
import datetime

class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str
    username: str
    avatar: str
    disc: str
    status: enums.Status
    bot: bool

    def __str__(self):
        """
        :return: Returns the username
        :rtype: str
        """
        return self.username

    def get_status(self):
        """
        :return: Returns a status object for the bot
        :rtype: Status
        """
        return Status(status = self.status)

class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    dup: bool
    bot_count: int
    bot_count_total: int

#LIBRARY-INTERNAL
class BotPromotionDelete(BaseModel):
    """
    Represents a promotion delete request. Your library should internally be using this but you shouldn't need to handle this yourself 
    """
    id: Optional[uuid.UUID] = None

class BotPromotionPartial(BaseModel):
    """
    Represents a partial bot promotion for creating promotions on Fates List

    A partial promotion is similar to a regular promotion object but does not have an id
    """
    title: str
    info: str
    css: Optional[str] = None
    type: int

class BotPromotion(BotPromotionPartial):
    """
    Represents a bot promotion on Fates List

    A partial promotion is similar to a regular promotion object but does not have an id
    """
    id: uuid.UUID

#LIBRARY-INTERNAL
class BotPromotionList(BaseModel):
    """
    This is a list of bot promotions. This should be handled by your library 
    """
    __root__: List[BotPromotion]

#LIBRARY-INTERNAL
class BotPromotionGet(BaseModel):
    """Represents a bot promotion response model. This should be handled by your library"""
    promotions: BotPromotionList

class BasePager(BaseModel):
    """Information given by the API for pagination"""
    total_count: int
    total_pages: int
    per_page: int
    from_: int
    to: int

    class Config:
        fields = {'from_': 'from'}

class APIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List CRUD endpoints

    You can check for success using the done boolean and reason using the reason attribute 
    
    Code is mostly random and for debugging other than 1000 and 1001 where 1000 means success and 1001 means success with message
    """
    done: bool
    reason: Optional[str] = None
    code: int = 1000

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

class BotListAdminRoute(BaseModel):
    mod: str

class BotStateUpdate(BaseModel):
    state: enums.BotState

class BotTransfer(BotListAdminRoute):
    new_owner: str

class BotUnderReview(BotListAdminRoute):
    requeue: Optional[bool] = False

class BotOwner(BaseModel):
    user: BaseUser
    main: bool

class BotOwners(BaseModel):
    __root__: List[BotOwner]

class VoteReminderPatch(BaseModel):
    remind: bool

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
    name: str
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: str

class BotCommand(PartialBotCommand):
    id: uuid.UUID
    
class BotCommandAddResponse(APIResponse):
    id: uuid.UUID

class BotCommands(BaseModel):
    __root__: Dict[uuid.UUID, BotCommand]

class BotCommandDelete(BaseModel):
    id: uuid.UUID

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
    current_time: str

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

class BotPromotion_NotFound(BaseModel):
    detail: str = "Promotion Not Found"
    code: int = 1001

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

class BotQueuePatch(BotListAdminRoute):
    feedback: Optional[str] = None 
    approve: bool

class BotQueueList(BaseModel):
    __root__: List[BaseUser]

class BotQueueGet(BaseModel):
    bots: BotQueueList

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
