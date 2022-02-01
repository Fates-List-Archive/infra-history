from modules.discord.api.v2.base_models import BaseUser, BotPack
from pydantic import BaseModel
from typing import Any, Optional, List
from modules.models import enums
from .badge import Badge
import datetime

class ProfileBot(BaseModel):
    """A bot attached to a users profile"""
    bot_id: int
    avatar: str | None = None
    description: str
    invite: str | None = None
    prefix: str | None = None
    banner: str | None = None
    state: enums.BotState
    votes: int
    guild_count: int
    nsfw: bool
    user: BaseUser | None = BaseUser()   
  
class BotLogs(BaseModel):
    bot_id: str
    action: int 
    action_time: datetime.datetime 
    context: Any

class ProfileData(BaseModel):
    """Misc data about a user"""
    badges: list[Badge]
    description: str | None = "This user prefers to be a enigma"
    user_css: str | None = ""
    profile_css: str | None = ""
    js_allowed: bool
    bot_developer: bool
    certified_developer: bool
    state: enums.UserState
    bot_logs: list[BotLogs] = None

class Profile(BaseModel):
    bots: list[ProfileBot]
    approved_bots: list[ProfileBot]
    certified_bots: list[ProfileBot]
    profile: ProfileData
    site_lang: str | None = None  # Not a part of profile because legacy code
    user: BaseUser
    bot_logs: list[dict] | None = None
    packs: list[BotPack]