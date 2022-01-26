import uuid
from typing import List, Optional
import datetime

from typing import Any

from pydantic import BaseModel

from modules.models import enums

from ..base_models import APIResponse, BaseUser

class GCVFormat(BaseModel):
    """Represents a formatted for client data"""
    guild_count: str
    votes: str

class BotRandom(BaseModel):
    """
    Represents a random bot on Fates List

    **Note:** Inline user fields are deprecated, use user instead
    """
    bot_id: str
    description: str
    banner_card: str | None = None
    state: int
    username: str
    avatar: str
    guild_count: int
    votes: int
    formatted: GCVFormat
    user: BaseUser

class BotOwner(BaseModel):
    user: BaseUser
    main: bool

class BotOwners(BaseModel):
    __root__: list[BotOwner]
        
class Bot(BaseModel):
    """
    Represents a bot on Fates List
    """
    user: BaseUser | None = None
    description: str | None = None
    tags: list[str]
    created_at: datetime.datetime
    last_stats_post: datetime.datetime | None = None
    long_description_type: enums.LongDescType | None = None
    long_description: str | None = None
    guild_count: int
    shard_count: int | None = 0
    user_count: int
    shards: list[int] | None = []
    prefix: str | None = None
    library: str
    invite: str | None = None
    invite_link: str
    invite_amount: int
    owners: BotOwners | None = None
    features: list[str]
    state: enums.BotState
    website: str | None = None
    support: str | None = None
    github: str | None = None
    css: str | None = None
    votes: int
    total_votes: int
    vanity: str
    donate: str | None = None
    privacy_policy: str | None = None
    nsfw: bool
    banner_card: str | None = None
    banner_page: str | None = None
    keep_banner_decor: bool | None = None
    client_id: str | None = None
    flags: list[int] | None = []
    action_logs: list[dict] | None = None
    uptime_checks_total: int | None = None
    uptime_checks_failed: int | None = None

class BotStats(BaseModel):
    guild_count: int
    shard_count: int | None = None
    shards: list[int] | None = None
    user_count: int | None = None
        
class BotEvent(BaseModel):
    m: dict
    ctx: dict

class BotEventList(BaseModel):
    __root__: list[BotEvent]

class BotEvents(BaseModel):
    events: BotEventList

class SettingsPage(BaseModel):
    data: dict[str, Any]
    context: dict[str, Any]