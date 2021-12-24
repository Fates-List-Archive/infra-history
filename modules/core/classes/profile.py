from pydantic import BaseModel
from typing import Optional, List
from modules.models import enums
from .badge import Badge

class ProfileBot(BaseModel):
    """A bot attached to a users profile"""
    bot_id: int
    avatar: str
    description: str
    invite: str
    prefix: str
    banner: str
    state: enums.BotState
    votes: int
    guild_count: int
    nsfw: bool       
  
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

class Profile(BaseModel):
    bots: list[ProfileBot]
    approved_bots: list[ProfileBot]
    certified_bots: list[ProfileBot]
    profile: ProfileData
    site_lang: str | None = None  # Not a part of profile because legacy code
    user: enums.BaseUser
    bot_logs: list[dict]   
