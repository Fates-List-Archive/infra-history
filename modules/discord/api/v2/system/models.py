from typing import Any, List, Optional

from pydantic import BaseModel

from modules.models import enums

from ..base_models import BaseUser, BotPack

class BotFeature(BaseModel):
    """
    Represents all of the features the list supports and information 
    about them. Keys indicate the feature id and value is 
    feature information. The value should but may 
    not always have a name, type and a description keys in the json
    """
    name: str
    type: str
    description: str

class BotFeatures(BaseModel):
    __root__: dict[str, BotFeature]


class FilteredBotOwner(BaseModel):
    user_id: str
    main: bool

class FilteredBotTag(BaseModel):
    tag: str

class PartialBotQueue(BaseModel):
    user: BaseUser | None = BaseUser()
    prefix: str | None = None
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
    features: BotFeatures | None = None


class Search(BaseModel):
    bots: list | None = []
    servers: list | None = []
    profiles: list | None = []
    packs: list[BotPack] | None = []
    tags: dict[str, FLTags]
    features: BotFeatures | None = None

class TagSearch(BaseModel):
    search_res: list
    tags_fixed: FLTags

class PartnerLinks(BaseModel):
    discord: str
    website: str

class Partner(BaseModel):
    id: str
    name: str
    owner: str
    image: str
    description: str
    links: PartnerLinks

class Partners(BaseModel):
    partners: list[Partner]
    icons: PartnerLinks

class StaffRole(BaseModel):
    """
    **Either fname (friendly name) or name may be defined.
    Check for both**
    """
    id: str
    staff_id: str
    perm: int
    name: str | None = ""
    fname: str | None = ""

class StaffRoles(BaseModel):
    __root__: dict[str, StaffRole]

class IsStaff(BaseModel):
    staff: bool
    perm: int
    sm: StaffRole

class SettingsPage(BaseModel):
    data: dict[str, Any]
    context: dict[str, Any]

class AddBotInfo(BaseModel):
    perm: int
    tags: list[str]
    features: list[str]

class Troubleshoot(BaseModel):
    req_user_agent: str | None = None
    pid: int
    cf_ip: str | None = None
    user: BaseUser | None = None

class BotStatsFull(BaseModel):
    bot_amount: int
    bot_amount_total: int
    denied_amount: int
    banned_amount: int
    certified: BotPartialList
    queue: BotPartialList
    under_review: BotPartialList
    denied: BotPartialList | None = None
    banned: BotPartialList | None = None
    uptime: float
    pid: int
    up: bool
    server_uptime: float
    workers: list[int]