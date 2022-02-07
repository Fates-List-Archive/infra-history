import uuid
from typing import List, Optional, Dict
import datetime

from pydantic import BaseModel

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser, GCVFormat

class GuildRandom(BaseModel):
    """
    Represents a random server/guild on Fates List
    """
    guild_id: str
    description: str
    banner_card: str | None = None
    state: int
    username: str
    avatar: str
    guild_count: int
    votes: int
    formatted: GCVFormat

class Guild(BaseModel):
    """
    Represents a server/guild on Fates List
    """
    invite_channel: str | None = None
    user: BaseUser
    description: str | None = None
    tags: list[dict[str, str]]
    long_description_type: enums.LongDescType | None = None
    long_description: str | None = None
    guild_count: int
    invite_amount: int
    total_votes: int
    user_whitelist: list[str] | None = None
    user_blacklist: list[str] | None = None
    state: enums.BotState
    website: str | None = None
    css: str | None = None
    votes: int
    vanity: str | None = None
    nsfw: bool
    banner_card: str | None = None
    banner_page: str | None = None
    keep_banner_decor: bool | None = None
