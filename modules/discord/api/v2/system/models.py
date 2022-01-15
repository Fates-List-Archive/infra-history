from typing import List, Optional

from pydantic import BaseModel

from modules.models import enums

from ..base_models import BaseUser


class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    server_uptime: float
    bot_count: int
    bot_count_total: int
    workers: list[int]


class FilteredBotOwner(BaseModel):
    user_id: str
    main: bool

class FilteredBotTag(BaseModel):
    tag: str

class PartialBotQueue(BaseModel):
    user: BaseUser | None = BaseUser()
    prefix: str
    invite: str
    description: str
    state: enums.BotState
    guild_count: int
    votes: int
    long_description: str
    website: str | None = None
    support: str | None = None
    owners: list[FilteredBotOwner]
    tags: list[FilteredBotTag]

class BotQueueList(BaseModel):
    __root__: list[PartialBotQueue]


class BotQueueGet(BaseModel):
    bots: BotQueueList | None = None


class BotVanity(BaseModel):
    type: enums.VanityType
    redirect: str


class BotPartial(BaseModel):
    description: str
    guild_count: int
    banner: str | None = None
    state: enums.BotState
    nsfw: bool
    votes: int
    user: BaseUser


class BotPartialList(BaseModel):
    __root__: list[BotPartial]


class FLTag(BaseModel):
    name: str
    iconify_data: str
    id: str
    owner_guild: str | None = ""


class FLTags(BaseModel):
    __root__: list[FLTag]


class BotIndex(BaseModel):
    tags_fixed: FLTags
    top_voted: BotPartialList
    certified_bots: BotPartialList
    new_bots: BotPartialList


class BaseSearch(BaseModel):
    tags_fixed: FLTags
    query: str


class BotSearch(BaseSearch):
    search_res: list
    profile_search: bool
