import uuid
from typing import Optional, Union

from pydantic import BaseModel

from modules.models import enums

import datetime

class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str | None = "0"
    username: str | None = "Unknown User"
    avatar: str | None = "https://fateslist.xyz/static/botlisticon.webp"
    disc: str | None = "0000"
    status: enums.Status | None = enums.Status.unknown
    bot: bool | None = True

    def __str__(self):
        """
        :return: Returns the username
        :rtype: str
        """
        return self.username

class BotPackPartial(BaseModel):
    """
    Represents a partial bot pack on fates list 
    (a bot pack without a id, owner or created_at)
    """
    name: str
    description: str
    icon: str | None = None
    banner: str | None = None
    bots: list[str]

class PackBot(BaseUser):
    description: str

class BotPack(BotPackPartial):
    """
    Represents a bot pack on fates list
    """
    id: uuid.UUID    
    created_at: datetime.datetime
    owner: BaseUser
    resolved_bots: list[PackBot]

class APIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List CRUD endpoints

    You can check for success using the done boolean and reason using the reason attribute 
    """
    done: bool
    reason: str | None = None

class HTMLAPIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List HTML endpoints
    """
    html: str

class IDResponse(APIResponse):
    id: uuid.UUID

class AccessToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    current_time: float | int

        
class BasePager(BaseModel):
    """Information given by the API for pagination"""
    total_count: int
    total_pages: int
    per_page: int
    from_: int
    to: int

    class Config:
        fields = {'from_': 'from'}
