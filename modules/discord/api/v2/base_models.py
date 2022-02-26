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

class APIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List CRUD endpoints

    You can check for success using the done boolean and reason using the reason attribute 
    """
    done: bool
    reason: str | None = None

class IDResponse(APIResponse):
    id: uuid.UUID

class GCVFormat(BaseModel):
    """Represents a formatted for client data"""
    guild_count: str
    votes: str